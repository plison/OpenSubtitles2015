# -*- coding: utf-8 -*- 

description = """
Convert srt files (movie subtitles) to tokenized XML (utf-8) based on a 
simple tokenization and sentence splitting procedure.

"""

import sys, os, io,json,re,gzip,tarfile,time,collections
import xml.etree.cElementTree as et
import utils
from utils import Tokeniser,SpellChecker
    
# Regex to detect the subtitle indices at the start of each block    
numberRegex = re.compile("(\d+)\r*\n")

# Regex to detect the start time --> end time line for each block
# (a bit complicated, since many variants are available)
timingRegex = re.compile("\s*(\-?\d+[:,\s\.]\s?\-?\d+[:,\s\.]\s?\-?\d+(?:[:,\s\.،]\s?\d+))\s*\-[\-\s]?"
                         + ">\s*(\-?\d+[:,\s\.]\s?\-?\d+[:,\s\.]\s?\-?\d+(?:[:,\s\.،]\s?\d+))")

# Regex to detect html tags
tagRegex = re.compile("<\s*\/?\s*?\w+(?:\s\w+(?:=['\"]?(?:.*?)['\"]?)?)*\s*?\/?\s*>")
# Regex to detect characters to remove
tostripRegex = re.compile("[" + re.escape('#$%&*+/<=>@[\\]^_{|}~') + "]")

# Regex to detect multiple occurrence of punctuation marks (except the dot)
toReduceRegex = re.compile(r"([\?!:,;]|\s)\1+")

# Sentence-ending markers
stopPunctuations = ['.','!','?', ':', ';','。','！','？', '；','：','؟','।']

# Quotation markers
quotationRegex = re.compile("``|''|[«»『「』」`‘’“›‹]")

# Regex to detect unlikely continuations between blocks
newLineRegex1 = re.compile("\s*([\"\'\[]?|[\*\#\']*\s*)(.)")
newLineRegex2 = re.compile("(\s*[\-\#\*\']*\s*[\"\'\[]?(.))")

PAUSE_THR1 = 1       # > 1 second --> most probably new sentence
PAUSE_THR2 = 3       # > 3 second --> definitely new sentence
WORDS_THR = 40       # Higher bound on number of words in sentence

    
class SubtitleConverter:

    def __init__(self, input, output, rawOutput=None, language=None, 
                meta=None, encoding=None, alwaysSplit=False):
        """Creates a new converter for a given input and output (as file
        objects). A second file object for the raw output can also be provided.
        
        Args:
            input(file object or list of file objects): raw subtitle files
            output(file object): XML subtitle file for the tokenised output
            rawOutput(file object): XML subtitle file for the untokenised output
            language(Language object): language for the subtitle
            meta(dict): meta-data to append to the end of the XML file(s)
            encoding(str): file encoding to use to read the raw subtitle files
            alwaysSplit(bool): whether to always split subtitle blocks as new 
                sentences (default is false).
        """
                    
        self.lang = language
        self.alwaysSplit = alwaysSplit
        self.inputs = input if isinstance(input,list) else [input]
        
        # The possible file encodings include both the initial encoding (if
        # provided) and language-specific encodings. If the language is not
        # specified or the number of alternative encodings is > 3, perform
        # automatic encoding detection with chardet.
        self.encodings = [encoding] if encoding else []
        self.encodings += (self.lang.encodings if self.lang else [])
        if not self.encodings:
            self.encodings = [detectEncoding(self.inputs[0])]
        elif len(self.encodings) > 3:
            detected = detectEncoding(self.inputs[0]).lower()
            if detected.rstrip("-sig") in self.encodings:
                self.encodings = [detected] + self.encodings
            else:
                raise RuntimeError("Encoding detection failed (%s)\n"%detected)
            
        self.output = output
        self.rawOutput = rawOutput   
        self.meta = meta         
        
    
    def doConversion(self):   
        """Performs the conversion process, reading the full subtitle file
        and writing the converted content into the output file.
        """  
             
        self.curLine = None         # Current line in the raw file
        self.curBlock = None        # Current block
        self.curLineIndex = 0       # Current line index in the raw file
        self.timeOffset = 0         # Time offset (for multi-CD subtitles)

        self.sid = 0                # Current sentence identifier
        self.nbWords = 0            # Total number of words
        self.nbIgnoredBlocks = 0    # Number of ignored subtitle blocks
        self.sentence = []          # Tokens in the current sentence
        self.text = []              # Collection of all subtitle lines
        self.rawSentence = ""       # Current raw sentence
        
        # Starting the tokeniser and spellchecker
        self.tokeniser = Tokeniser(self.lang)
        self.spellchecker = SpellChecker(self.lang)
        
        self._startDocument()       
    
        # Looping on the subtitle blocks
        block = self._readBlock()
        while block:
                    
            # Ignoring spurious subtitle blocks    
            if block.isSpurious():
                self.nbIgnoredBlocks += 1
                block = self._readBlock()
                continue

            # Handling bilingual subtitles (e.g. 'zhe' subtitles)
            if self.lang and self.lang.second_language:
                self._writeBlock_bilingual(block)
            # standard case       
            else:
                self._writeBlock(block) 
            
            # We record the text content for language identification purposes
            self.text += block.lines
            
            block = self._readBlock()
            
        self._flushDocument()
        self.tokeniser.close()
        
       
    def _startDocument(self):
        """Writes the header of the XML subtitle file. 
        
        """
        
        id = self.meta["id"] if self.meta and "id" in self.meta else ""
        if not id and self.inputs and  hasattr(self.inputs[0],"name"):
            id = os.path.basename(self.inputs[0].name).split(".")[0]
        id = id.encode("utf-8")
            
        self.output.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
        self.output.write(b'<document id="' + id + b'">\n')
        if self.rawOutput:
            self.rawOutput.write(b'<?xml version="1.0" encoding="utf-8"?>\n')
            self.rawOutput.write(b'<document id="' + id + b'">\n') 
              
   
    def _readBlock(self):
        """Reads one subtitle block and returns it.
        
        """

        block = SubtitleBlock()
        block.previous = self.curBlock
        block.offset = self.timeOffset
        
        # Reads the very first line
        if not self.curLine:
            self._readline()
            
        # Continues until a non-empty line is found
        while self.curLine and not self.curLine.strip():
            self._readline()

        # If we arrive at the end of the file object, checks whether any
        # other file should be read (in case of multi-CD subtitles). If yes,
        # opens the new file and continue.  Else, returns None.
        if not self.curLine:
            self.inputs.pop(0)
            self.curLineIndex = 0
            
            # shifting the start and end times after the first CD
            if block.previous:
                self.timeOffset += tosecs(block.previous.end)
            return self._readBlock() if self.inputs else None
                  
        # Detects the subtitle identifier
        numberMatch = numberRegex.match(self.curLine)
        if numberMatch:
            block.setId(int(numberMatch.group(1)))
            self._readline()
        else:        
            block.setId((self.curBlock.id+1) if self.curBlock else 1)
         
        # Ignores empty lines
        while self.curLine and not self.curLine.strip():
            self._readline() 
            
        # Detects the start and end time           
        timingMatch = timingRegex.match(self.curLine)
        if not timingMatch:
            sys.stderr.write("Cannot parse timing (line number: %i): %s"
                             %(self.curLineIndex, self.curLine))
            self._readline()
            self.nbIgnoredBlocks += 1
            return self._readBlock()
        block.setTiming(timingMatch.group(1), timingMatch.group(2)) 
   
        # Reads the subtitle content until we arrive at the next subtitle ID
        # or the end of the file (NB: simply stopping at an empty line does
        # not always work, since some files strangely contain empty lines 
        # within subtitle blocks).
        self._readline()
        while self.curLine.strip():
            block.addLine(self.curLine)
            self._readline()          
        while self.curLine and not numberRegex.match(self.curLine):
            block.addLine(self.curLine)
            self._readline()

        self.curBlock = block
        return block
    
    
    def _readline(self):
        """ Reads the next line in the file, decodes it according to the
        current encoding, and returns it. If a decoding error is detected,
        tries to change the encoding if an alternative is possible.
        
        """
        if self.inputs:
            binaryLine = self.inputs[0].readline()
        self.curLine = None
        while self.curLine==None and self.encodings:
            encoding = self.encodings[0]
            try:
                self.curLine = binaryLine.decode(encoding)
            except UnicodeDecodeError:
                # If we get a decoding error, removes the encoding from
                # the list of possible encodings, and retry.
                self.encodings.remove(encoding)

        if self.curLine==None:
            raise RuntimeError("Decoding error (encoding: %s, line: %i)"
                             %(encoding, self.curLineIndex))
        elif self.curLineIndex==0:
            self.curLine = self.curLine.lstrip("\ufeff")

        self.curLineIndex += 1
  
                      
    def _writeBlock(self, block):
        """ Processes the block content by doing sentence segmentation, 
        tokenisation, and writes the results into the XML file.
        
        """
        
        # First check whether the block is a continuation of the previous
        # sentence. If not, "flush" the current sentence to start a new one.
        if not self._isContinuation(block):    
            self._flushSentence()
         
        self.sentence.append(("time", "T%sS"%block.id, block.start))
        
        # Loops on each line of the subtitle block
        for linenum, line in enumerate(block.lines):
            
            self.rawSentence += " " if self.rawSentence else ""
            lastLine = linenum==len(block.lines)-1
            self._recordLine(line, lastLine)
            
        self.sentence.append(("time", "T%sE"%block.id, block.end))
   
    
    def _writeBlock_bilingual(self, block):
        """Processes the block content (doing sentence segmentation and 
        tokenisation) in the particular case of "bilingual" subtitles, where
        two languages are used in the subtitle (one on each line).
        
        In this setting, we always split sentences at the end of each block.
        
        """
               
        for linenum, line in enumerate(block.lines):
            
            self.sentence = [("time", "T%sS"%block.id, block.start)]
         
            # Adding an attribute on each <s> to indicate the 
            # language (1 or 2) of the sentence
            flags = {"lang":str(linenum+1)}
            lastLine = linenum==len(block.lines)-1
            self._recordLine(line, lastLine, flags)
            
            self.sentence.append(("time", "T%sE"%block.id, block.end))
            self._flushSentence(flags)
  
  
    def _recordLine(self, line, lastLine, flags={}):
        """ Records the subtitle line, checking for the occurrence of 
        end-of-sentence markers along the way, and flushing the current 
        sentence in that case.
        
        """
        
        # Doing the actual tokenisation
        if lastLine and self.tokeniser.secondTokeniser:
            tokens = self.tokeniser.secondTokeniser.tokenise(line)
        else:
            tokens = self.tokeniser.tokenise(line)
         
        lineIndex = 0       # Current character position in the line
        for i, token in enumerate(tokens):  
            
            # Assume a new sentence if an utterance started with "-" is found   
            # (and ignores that token)  
            if token=="-" and i < len(tokens)-1:
                self._flushSentence(flags)
                lineIndex += 1             
                
            # Else, append the token 
            else:
                corrected = self.spellchecker.spellcheck(token)
                self.sentence.append(("w", corrected))
                self.rawSentence += corrected
                lineIndex += len(token)
            while lineIndex < len(line) and line[lineIndex].isspace():
                self.rawSentence += line[lineIndex]
                lineIndex += 1
                
            # Do not flush the sentence for the last token in the last line
            if lastLine and i==len(tokens)-1:
                continue
            
            # Flush the sentence if we have a punctuation mark followed by a 
            # new line or an uppercase next character (if language not unicase)
            elif token[0] in stopPunctuations:
                if (i==len(tokens)-1 or tokens[i+1][0].isupper() 
                    or (self.lang and self.lang.unicase)):
                    self._flushSentence(flags)
   
    
    def _isContinuation(self, block):
        """Returns true if the block is likely to be a continuation of the current
        sentence
        
        """
        if not self.sentence or not block.lines:
            return True
        elif self.alwaysSplit:
            return False
    
        line = block.lines[0]
        lastToken = next((x[1] for x in reversed(self.sentence) if x[0]=="w"), None)
        
        # Returns true if last line ends with ... and new block starts with ...
        if lastToken=="..." and (line.startswith("...") or line.islower()):
            return True
        
        # Returns false if we have a "-" starting the block
        elif line.startswith("-"):
            return False
        
        # Calculates a score given the time gap between the blocks and the length
        # of the previous block
        score = (3 if lastToken and lastToken[0] in stopPunctuations else 1)
        lastStamp = next((x[2] for x in reversed(self.sentence) if x[0]=="time"), None)
        if block.start and lastStamp:
            pause = tosecs(block.start) - tosecs(lastStamp)
            score += (1 if pause > PAUSE_THR1 else 0)
            score += (1 if pause > PAUSE_THR2 else 0)
            score += (1 if len([x for x in self.sentence if x[0]=="time"]) >2 else 0)
            score += (1 if len(self.sentence) > WORDS_THR else 0)      
        if score >= 3:
            return False     
        
        # Handling border-line cases (when special characters are in the way)
        match = newLineRegex1.match(line)
        validchar = lambda c : c.isupper() or c in ["¿", "¡"]
        if match and validchar(match.group(2)):
            return False
        match = newLineRegex2.match(line)
        validchar = lambda c : c.isupper() or c.isnumeric() or c in ['(', '[']
        if match and score >= 2 and validchar(match.group(2)):
            return False
        return True


    def _flushSentence(self, flags={}):
        """ Writes the tokens to the XML file (and the untokenised output if
        that option is activated) and clears the current sentence.
        
        """ 
        nbWords = len([t for t in self.sentence if t[0]=="w"])
        if not nbWords:
            return
        self.nbWords += nbWords 
        self.sid += 1
        self._writeTokens(flags)
        if self.rawOutput:
            self._writeRaw(flags)
        self.sentence = [] 
        self.rawSentence = ""   
  
          
    def _writeTokens(self, flags={}):
        """ Writes the tokens in self.sentence to the XML file. 
        
        The flags are appended to the attribute of the <s> entity.
        
        """
        builder = et.TreeBuilder()  
        attrs =  {"id":str(self.sid)}
        attrs.update(flags)
        builder.start("s",attrs)
        tokid = 0
        for i, entity in enumerate(self.sentence):
            
            if entity[0]=="w":
                token = entity[1]
                if i < len(self.sentence)-1 and token=="...":
                    continue
                tokid += 1
              
                builder.data("\n    ")
                builder.start("w",{"id":"%i.%i"%(self.sid,tokid)})
                builder.data(token)
                builder.end("w") 
                     
            # Write a <time> entity
            elif entity[0]=="time":
                builder.data("\n    ")
                builder.start("time",{"id":entity[1], "value":entity[2]})
                builder.end("time")    
          
        builder.data("\n  ")
        builder.end("s")
        tree = et.ElementTree(builder.close())
        self.output.write(b"  ")
        tree.write(self.output, encoding='utf-8')
        self.output.write(b"\n") 
        
        
               
    def _writeRaw(self, flags={}):
        """ Writes the raw sentence in self.rawSentence to the XML file. 
        
        The flags are appended to the attribute of the <s> entity.
        
        """
        builder = et.TreeBuilder()  
        attrs =  {"id":str(self.sid)}
        attrs.update(flags)
        builder.start("s",attrs)

        # Add timing info at the beginning of the sentence
        if self.sentence and self.sentence[0][0] == "time":
            builder.data("\n    ")
            builder.start("time",{"id":self.sentence[0][1], "value":self.sentence[0][2]})
            builder.end("time")  
            
        builder.data("\n")
        builder.data(self.rawSentence)
          
        # Add timing info at the end of the sentence
        if self.sentence and self.sentence[-1][0] == "time":
            builder.data("\n    ")
            builder.start("time",{"id":self.sentence[-1][1], "value":self.sentence[-1][2]})
            builder.end("time")   
          
        builder.data("\n  ")
        builder.end("s")
        tree = et.ElementTree(builder.close())
        self.rawOutput.write(b"  ")
        tree.write(self.rawOutput, encoding='utf-8')
        self.rawOutput.write(b"\n") 
    
    
    
    def _extractMetadata(self):
        """ Extracts meta-data on the subtitle and the conversion process,
        in order to append it to the end of the XML file.
        
        """
        meta = self.meta if self.meta else {}
        if "id" in meta:
            del meta["id"]
        meta["subtitle"] = meta["subtitle"] if "subtitle" in meta else {}
        if self.lang:
             meta["subtitle"]["language"] = self.lang.name
             text = " ".join(self.text)
             
             # Performs language identification
             meta["subtitle"]["confidence"] = str(self.lang.getProb(text))
        for x in reversed(self.sentence):
            if x[0]=="time":
                meta["subtitle"]["blocks"] = x[1][1:-1]
                meta["subtitle"]["duration"] = x[2].split(",")[0]
                break
        meta["conversion"] = {}
        meta["conversion"]["sentences"] = str(self.sid + 1)
        meta["conversion"]["words"] = str(self.nbWords + len(self.sentence))
        meta["conversion"]["encoding"] = self.encodings[0]
        meta["conversion"]["ignored_blocks"] = str(self.nbIgnoredBlocks)
        if self.spellchecker.dictionary:
            sc = self.spellchecker
            meta["conversion"]["unknown_words"] = str(sc.nbUnknowns)
            meta["conversion"]["corrected_words"] = str(sc.nbCorrections)
        return meta
    
    
    def _flushDocument(self):
        """ Adds the final meta-data to the XML file, and closes the XML document.
        
        """
        meta = self._extractMetadata()
        self._flushSentence()
        metaBuilder = et.TreeBuilder()
        metaBuilder.start("meta")
        
        for part in meta:
            metaBuilder.data("\n    ")
            metaBuilder.start(part)
            if isinstance(meta[part],dict):
                for key in meta[part]:
                    metaBuilder.data("\n      ")
                    metaBuilder.start(key)
                    metaBuilder.data(meta[part][key])
                    metaBuilder.end(key)
            metaBuilder.data("\n    ")
            metaBuilder.end(part)
        
        metaBuilder.data("\n  ")   
        metaBuilder.end("meta")
        tree = et.ElementTree(metaBuilder.close())
        for fd in [self.output,self.rawOutput]:
            if fd:
                fd.write(b"  ")
                tree.write(fd, encoding='utf-8')
                fd.write(b"\n</document>\n") 


class SubtitleBlock:
    """Representation of a subtitle block (with an identifier, a start time, 
    an end time, and a list of (usually 1 or 2) lines.
    
    """
    
    def __init__(self):
        """Initialises the block. """
        self.lines = []
        self.start = None
        self.end = None
        self.previous = None
        self.offset = 0
        
    def setId(self, id):
        """Sets the block identifier. """
        self.id = id
         
    def setTiming(self, start, end):
        """Sets the timing for the block (in seconds). """
        self.start = addsecs(start, self.offset)
        self.end = addsecs(end, self.offset)      
    
    def addLine(self, line):
        """Adds the line to the block. The method also strips html tags,
        spurious characters and punctuations, and non-standard quotation marks.
        
        """
        line = line.strip()
        if not line:
            return
        line = tagRegex.sub("", line)
        line = tostripRegex.sub("", line)  
        line = quotationRegex.sub("\"", line)  
        line = line.replace("…", "...").replace("‥", "...")
        line = toReduceRegex.sub("\g<1>", line)
        self.lines.append(line)
    
    def __str__(self):
        """Returns a string representation of the block.
        
        """
        s = ""
        if self.id:
            s += str(self.id) + "\n"
        if self.start and self.end:
            s += self.start + " --> " + self.end + "\n"
        s += "\n".join(self.lines)
        return s
    
    def isSpurious(self):
        """Returns true if the block is considered as "purious, i.e.
        if it contains an URL, the "opensubtitles" mention, or is a 
        "moving" subtitle (with one single character appended to the 
        previous block).
        
        """
        if not self.start or not self.end:
            return True
        for l in self.lines:
            l2 = l.lower()
            if ("http" in l2 or "www" in l2 or "opensubtitles" in l2
                or ".com" in l2):
                return True
            
        if self.previous:
            curStr = " ".join(self.lines)  
            prevStr = " ".join(self.previous.lines)
            for i in range(0,3):
                if len(curStr)==len(prevStr)+i and curStr[:-i]==prevStr:
                    return True
        return False
                 
        

def convertSubtitle(srtFile=None, xmlFile=None, langcode=None,encoding=None, 
                    alwaysSplit=False, rawOutput=None,meta=None):
    """Converts a .srt subtitle to the XML representation.  
    
    Args:
        srtFile(file path or None): path to the srt file. If set to None,
            reads from standard input
        xmlFile(file path or None): path to the XML output file. If set to
            None, write to the standard output
        langcode(str): 2- or 3-letters code for the subtitle language
        encoding(str): file encoding for the subtitle.
        alwaysSplit(bool): whether to systematically consider each block
            to start a new sentence.
        rawOutput(file path or None): path to the XML file for the (untokenised)
            output. Leave to None to avoid generating this output.
        meta(dict): Meta-data about the subtitle to write at the end of the 
            XML file(s).
            
    """
    if srtFile:
        input = io.open(srtFile,mode='rb') 
    else:
        input = io.TextIOWrapper(sys.stdin.buffer,mode='rb')
        
    output = io.open(xmlFile,'wb') if xmlFile else sys.stdout.buffer
    rawOutput = io.open(rawOutput,'wb') if rawOutput else None

    lang = utils.getLanguage(langcode) if langcode else None
    converter = SubtitleConverter([input],output,rawOutput,lang,
                                  meta, encoding,alwaysSplit)
    converter.doConversion()
    
    if output != sys.stdout.buffer:
        output.close()
    if rawOutput:
        rawOutput.close()
     
     
def detectEncoding(input,nbChars=2000):
    """Tries to detected the encoding using chardet.  First tries to
    perform the detection with a limited number of characters (since the
    operation is computational expensive), and retries the detection on
    the full file if the confidence remains below a given threshold.
    
    Args:
        input (file object): the input to process
        nbChars(int): number of characters to consider.
        
    """
    if not input or not hasattr(input,"fileno"):
        return "utf-8"
    try:
        import chardet
    except RuntimeError:
        sys.stderr.write("Cannot find chardet\n")
        return "utf-8"

    firstBytes = b''
    for line in input:
        if line and len(firstBytes) < nbChars:
            if not chr(line[0]).isnumeric():
                firstBytes  += line
        else:
            break
    result =chardet.detect(firstBytes)
    sys.stderr.write("Detected encoding: %s with confidence %f\n"
                       %(result['encoding'], result['confidence']))
    
    #Resetting position to the start of the file
    input.seek(0)
    if result['confidence'] > 0.7:
        return result['encoding'].lower()
    elif line:
        return detectEncoding(input,nbChars*5)
    else:
        raise RuntimeError("Cannot detect file encoding, aborting")
      

def tosecs(timeStr):
    """ Convers the time string as a number of seconds.
    
    """
    if not timeStr:
        return 0
    split = re.split("[^0-9\-]",timeStr)
    split = [s for s in split if s]
    if len(split) >=3:
        secs = 3600*int(split[0]) + 60*int(split[1]) + int(split[2])
    else:
        return 0
    if len(split)==4:
        secs += int(split[3])/1000.0
    return secs

def addsecs(timeStr, offset):
    """ Adds a number of seconds to the given time string.
    
    """
    if not offset:
        return timeStr
    totalSecs = tosecs(timeStr) + offset
    m, s = divmod(totalSecs, 60)
    h, m = divmod(m, 60)
    return "%02d:%02d:"%(h,m) + ("%.3f"%s).replace(".",",")

 
        
if __name__ == '__main__':
    """ Parse the command line arguments. 
    
    """
    import argparse
 
    cmdOptions = argparse.ArgumentParser(prog="srt2xml", description=description)
    cmdOptions.add_argument("srtFile", nargs='?',
                               help="Path to the subtitle file in srt format")
    cmdOptions.add_argument("xmlFile", 
                          help="""Path to the output XML file. If omitted, 
                          writes to the standard output""", nargs='?')
    cmdOptions.add_argument("-r", dest="rawOutput", 
                          help="raw XML output file (without tokenization)")
    cmdOptions.add_argument("-l", dest="langcode", help="language code (ISO-639-3)")
    cmdOptions.add_argument("-e",dest="encoding",  
                          help="text encoding for the srt-file (if omitted, try to detect automatically)")
    cmdOptions.add_argument("-s", dest="alwaysSplit", action='store_true', 
                          help="always start a new sentence at new time frames (default is false)")

    cmdOptions.add_argument("-m", dest="meta", help="meta-data")


    args = vars(cmdOptions.parse_args())
    if args["meta"]:
        args["meta"]=json.loads(args["meta"])
  
    convertSubtitle(**args)  
        
    
   
        
        