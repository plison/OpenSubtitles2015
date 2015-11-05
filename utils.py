
import os, json, io, collections, re, unicodedata, sys, errno
from subprocess import Popen, PIPE

# Language data (codes, names, encodings, scripts, dictionaries)
languages = {'alb': 'sq', 'scc': 'sr', 'ita': 'it', 'per': 'fa', 'gl': {'codes':
['glg', 'gl'], 'name': 'Galician', 'scripts': ['latin'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'mne': 'me', 'ell': 'el', 'hrv': 'hr', 'tr':
{'codes': ['tur', 'tr'], 'name': 'Turkish', 'scripts': ['latin'], 'encodings':
['utf-8', 'windows-1254', 'iso-8859-9']}, 'lv': {'codes': ['lav', 'lv'], 'name':
'Latvian', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'lt': {'codes': ['lit', 'lt'], 'name': 'Lithuanian', 'scripts':
['latin'], 'encodings': ['utf-8', 'windows-1257', 'iso-8859-4']}, 'nor': 'no',
'th': {'codes': ['tha', 'th'], 'name': 'Thai', 'scripts': ['thai'], 'encodings':
['utf-8', 'tis-620']}, 'te': {'codes': ['tel', 'te'], 'name':
'Telugu', 'scripts': ['telugu'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'fin': 'fi', 'ta': {'codes': ['tam', 'ta'], 'name': 'Tamil',
'scripts': ['tamil'], 'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']},
'ger': 'de', 'dan': 'da', 'de': {'scripts': ['latin'], 'codes': ['ger', 'de'],
'name': 'German', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/de.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'da': {'codes': ['dan', 'da'], 'name':
'Danish', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'mon': 'mn', 'geo': 'ka', 'hin': 'hi', 'baq': 'eu', 'el':
{'codes': ['ell', 'el'], 'name': 'Greek', 'scripts': ['greek'], 'encodings':
['utf-8', 'windows-1253', 'iso-8859-7']}, 'eo': {'codes': ['epo', 'eo'], 'name':
'Esperanto', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'en': {'scripts': ['latin'], 'codes': ['eng', 'en'], 'name':
'English', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/en.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'tel': 'te', 
'ara': 'ar','eu': {'codes': ['baq', 'eu'], 'name': 'Basque', 'scripts': ['latin'],
'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'et': {'codes': ['est',
'et'], 'name': 'Estonian', 'scripts': ['latin'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'ur': {'codes': ['urd', 'ur'], 'name': 'Urdu',
'scripts': ['arabic'], 'encodings': ['utf-8', 'windows-1256', 'iso-8859-6']},
'arm': 'hy', 'es': {'scripts': ['latin'], 'codes': ['spa', 'es'], 'name':
'Spanish', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/es.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'ru': {'codes': ['rus', 'ru'], 'name':
'Russian', 'scripts': ['cyrillic'], 'encodings': ['utf-8','koi8-r','windows-1251',
'maccyrillic','iso-8859-5','ibm855','ibm866']},'est': 'et', 'ice': 'is', 'ro': {'scripts':
['latin'], 'codes': ['rum', 'ro'], 'name': 'Romanian', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/ro.dic', 'encodings':
['utf-8', 'windows-1250', 'iso-8859-2']}, 'tur': 'tr', 'be': {'codes': ['bel',
'be'], 'name': 'Belarusian', 'scripts': ['cyrillic'], 'encodings': ['utf-8',
'koi8-r', 'windows-1251', 'iso-8859-5']}, 'bg': {'codes': ['bul', 'bg'], 'name':
'Bulgarian', 'scripts': ['cyrillic'], 'encodings': ['utf-8', 'windows-1251',
'iso-8859-5']}, 'uk': {'codes': ['ukr', 'uk'], 'name': 'Ukrainian', 'scripts':
['cyrillic'], 'encodings': ['utf-8', 'windows-1251', 'koi8-u', 'iso-8859-5']},
'rum': 'ro', 'bn': {'codes': ['ben', 'bn'], 'name': 'Bengali', 'scripts':
['bengali'], 'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'br':
{'codes': ['bre', 'br'], 'name': 'Breton', 'scripts': ['latin'], 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'bs': {'codes': ['bos', 'bs'], 'name':
'Bosnian', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1250',
'iso-8859-2']}, 'rus': 'ru', 'ja': {'codes': ['jpn', 'ja'], 'name': 'Japanese',
'scripts': ['japanese'], 'encodings': ['utf-8', 'shiftjis','euc-jp', 'iso-2022-jp']}, 
'pt': {'scripts':['latin'], 'codes': ['por', 'pt'], 'name': 'Portuguese', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/pt.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'bos': 'bs', 'glg': 'gl', 'vie': 'vi',
'ca': {'codes': ['cat', 'ca'], 'name': 'Catalan', 'scripts': ['latin'],
'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'por': 'pt', 'ukr': 'uk',
'pol': 'pl', 'fi': {'codes': ['fin', 'fi'], 'name': 'Finnish', 'scripts':
['latin'], 'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'cs':
{'scripts': ['latin'], 'codes': ['cze', 'cs'], 'name': 'Czech', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/cz.dic', 'encodings':
['utf-8', 'windows-1250', 'iso-8859-2']}, 'zh': {'codes': ['chi', 'zh'], 'name':
'Chinese (simplified)', 'scripts': ['chinese'], 'encodings': ['utf-8', 'big5',
'gb2312', 'gb18030','hz-gb-2312']}, 'bre': 'br', 'pob': 'pb', 'tgl': 'tl', 'fre': 'fr', 'chi': 'zh',
'af': {'codes': ['afr', 'af'], 'name': 'Afrikaans', 'scripts': ['latin'],
'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'swe': 'sv', 'tl':
{'codes': ['tgl', 'tl'], 'name': 'Tagalog', 'scripts': ['latin'], 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'pb': {'scripts': ['latin'], 'codes':
['pob', 'pb'], 'name': 'Portuguese (BR)', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/pt.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'heb': 'he', 'kor': 'ko', 'dut': 'nl',
'pl': {'scripts': ['latin'], 'codes': ['pol', 'pl'], 'name': 'Polish',
'dictionary': '/projects/researchers/researchers01/plison/data/ngrams/pl.dic',
'encodings': ['utf-8', 'windows-1250', 'iso-8859-2']}, 'hy': {'codes': ['arm',
'hy'], 'name': 'Armenian', 'scripts': ['latin'], 'encodings': ['utf-8']}, 'hr': {'codes': ['hrv', 'hr'], 'name':
'Croatian', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1250',
'iso-8859-2']}, 'hun': 'hu', 'hu': {'codes': ['hun', 'hu'], 'name': 'Hungarian',
'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1250', 'iso-8859-2']},
'hi': {'codes': ['hin', 'hi'], 'name': 'Hindi', 'scripts': ['devanagari'],
'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'bul': 'bg', 'he':
{'codes': ['heb', 'he'], 'name': 'Hebrew', 'scripts': ['hebrew'], 'encodings':
['utf-8', 'windows-1255', 'iso-8859-8']}, 'me': {'codes': ['mne', 'me'], 'name':
'Montenegrin', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'ben': 'bn', 'zht': 'zt', 'bel': 'be', 'ml': {'codes': ['mal',
'ml'], 'name': 'Malayalam', 'scripts': ['malayalam'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'slv': 'sl', 'mn': {'codes': ['mon', 'mn'],
'name': 'Mongolian', 'scripts': ['mongolian'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'mk': {'codes': ['mac', 'mk'], 'name':
'Macedonian', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1251',
'iso-8859-5']}, 'cat': 'ca', 'slo': 'sk', 'zhe': 'ze', 'ms': {'codes': ['may',
'ms'], 'name': 'Malay', 'scripts': ['latin'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'my': {'codes': ['bur', 'my'], 'name':
'Burmese', 'scripts': ['burmese'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'jpn': 'ja', 'vi': {'codes': ['vie', 'vi'], 'name':
'Vietnamese', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1258',
'iso-8859-1']}, 'is': {'codes': ['ice', 'is'], 'name': 'Icelandic', 'scripts':
['latin'], 'encodings': ['utf-8', 'iso-8859-4']}, 'it': {'scripts': ['latin'],
'codes': ['ita', 'it'], 'name': 'Italian', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/it.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'zt': {'codes': ['zht', 'zt', 'zh'], 'name':
'Chinese (traditional)', 'scripts': ['chinese'], 'encodings': ['utf-8', 'big5',
'gb2312', 'gb18030','hz-gb-2312']}, 'ar': {'codes': ['ara', 'ar'], 'name': 'Arabic', 'scripts':
['arabic'], 'encodings': ['utf-8', 'windows-1256', 'iso-8859-6']}, 'khm': 'km',
'tam': 'ta', 'ind': 'id', 'spa': 'es', 'id': {'codes': ['ind', 'id'], 'name':
'Indonesian', 'scripts': ['latin'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'cze': 'cs', 'nl': {'scripts': ['latin'], 'codes': ['dut',
'nl'], 'name': 'Dutch', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/nl.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'eng': 'en', 'lit': 'lt', 'bur': 'my',
'sin': 'si', 'afr': 'af', 'fr': {'scripts': ['latin'], 'codes': ['fre', 'fr'],
'name': 'French', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/fr.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'may': 'ms', 'fa': {'codes': ['per',
'fa'], 'name': 'Persian', 'scripts': ['arabic'], 'encodings': ['utf-8',
'windows-1256', 'mac_farsi', 'iso-8859-6']}, 'mac': 'mk', 'kaz': 'kk', 'lav': 'lv', 
'mal':'ml', 'urd': 'ur', 'ka': {'codes': ['geo', 'ka'], 'name': 'Georgian', 'scripts':
['georgian'], 'encodings': ['utf-8','georgian-ps']}, 'kk':
{'codes': ['kaz', 'kk'], 'name': 'Kazakh', 'scripts': ['cyrillic'], 'encodings':
['utf-8', 'windows-1251', 'windows-1252', 'koi8-r', 'iso-8859-1']}, 
'sr': {'codes': ['scc', 'sr'], 'name':'Serbian', 'scripts': ['latin', 'cyrillic'], 
'encodings': ['utf-8','windows-1250', 'windows-1251', 'windows-1252', 'iso-8859-2', 
'iso-8859-5']},'sq': {'codes': ['alb', 'sq'], 'name': 'Albanian', 'scripts': ['latin'],
'encodings': ['utf-8', 'windows-1250', 'iso-8859-2']}, 'no': {'codes': ['nor',
'no'], 'name': 'Norwegian', 'scripts': ['latin'], 'encodings': ['utf-8',
'windows-1252', 'iso-8859-1']}, 'ko': {'codes': ['kor', 'ko'], 'name': 'Korean',
'scripts': ['korean'], 'encodings': ['utf-8', 'euc_kr','iso-2022-kr']}, 'sv': {'scripts':
['latin'], 'codes': ['swe', 'sv'], 'name': 'Swedish', 'dictionary':
'/projects/researchers/researchers01/plison/data/ngrams/se.dic', 'encodings':
['utf-8', 'windows-1252', 'iso-8859-1']}, 'km': {'codes': ['khm', 'km'], 'name':
'Khmer', 'scripts': ['khmer'], 'encodings': ['utf-8', 'windows-1252',
'iso-8859-1']}, 'sk': {'codes': ['slo', 'sk'], 'name': 'Slovak', 'scripts':
['latin'], 'encodings': ['utf-8', 'windows-1250', 'iso-8859-2']}, 'epo': 'eo',
'si': {'codes': ['sin', 'si'], 'name': 'Sinhalese', 'scripts': ['sinhala'],
'encodings': ['utf-8', 'windows-1252', 'iso-8859-1']}, 'sl': {'codes': ['slv',
'sl'], 'name': 'Slovenian', 'scripts': ['latin'], 'encodings': ['utf-8',
'windows-1250', 'iso-8859-2']}, 'tha': 'th'}


# Path to tokenisation script
tokeniserPath = "/cluster/home/plison/mt/mosesdecoder/scripts/tokenizer/tokenizer.perl"

# Path and models for the Kytea sentence segmentation tool
kyteaPath = "/cluster/home/plison/mt/kytea"
kyteaModels = {"ja": "/cluster/home/plison/mt/kytea/models/jp-0.4.7-5.mod",
               "zh": "/cluster/home/plison/mt/kytea/models/lcmc-0.4.0-1.mod"}

os.environ["LD_LIBRARY_PATH"] += ":" + kyteaPath + "/lib"
       
class Tokeniser():
    """Tokeniser (and spelling corrector)."""
    
    def __init__(self, language=None):
        """Initialises the tokeniser and dictionary for a particular language.
        
        Args:
            language(Language object): language for the tokeniser (None if unknown).
        
        """
        
        # Starts a process with the tokeniser tool
        if language and "Japanese" in language.name:
            self.cmd = kyteaPath + "/bin/kytea -notags -model " + kyteaModels["ja"]
        elif language and "Chinese" in language.name:
            self.cmd = kyteaPath + "/bin/kytea -notags -model " + kyteaModels["zh"]
        else:
            self.cmd = tokeniserPath + " -no-escape -q -b "
            self.cmd += ("-l %s" % language.codes[-1] if language else "")       
        self.tokprocess = Popen(self.cmd, 1, shell=True, stdin=PIPE, stdout=PIPE)
        
        self.language = language
         
  
    def tokenise(self, sentence):
        """Tokenises the given sentence and corrects the tokens 
        with OCR errors or misplaced accents
        
        """
        try:
            self.tokprocess.stdin.write((sentence + "\n").encode('utf-8'))
            self.tokprocess.stdin.flush()
        except IOError as e:
            sys.stderr.write("Error: " + str(e) + "\n")
            if e.errno == errno.EPIPE or e.errno == errno.EINVAL:
                return []
            else:
                raise
        if self.tokprocess.poll() == None:
            sentence = self.tokprocess.stdout.readline().decode('utf-8')
        
        sentence = sentence.replace(". . .", "...")
        if "kytea" in self.cmd:
            sentence = sentence.replace("\\", "")
            
        tokens = sentence.split()
        
        corrected = []
        while tokens:      
            token = tokens.pop(0)
            if token.startswith("-"):
                corrected.append("-")
                token = token[1:]
            if not token:
                continue
            corrected.append(token)            
        return corrected
    
    
    def close(self):
        """Closes the tokenisation processes."""
        
        self.tokprocess.terminate()
        self.tokprocess.stdin.close()
        self.tokprocess.stdout.close()
    

class SpellChecker():
   
   def __init__(self, language=None):
       self.dictionary = language.getDictionary() if language else None
       self.nbUnknowns = 0
       self.nbCorrections = 0
       
       
   def spellcheck(self, word):
        """Spell-check the word.  The method first checks if the word is in the
        dictionary.  If yes, the word is returned.  Else, the method search for
        a possible correction, and returns it.  If no correction could be found,
        the initial word is returned.  
        
        """    
        if not word.isalpha() or not word[0].islower():
            return word
        elif self.dictionary and not self.dictionary.isWord(word):
            self.nbUnknowns += 1
            correction = self._correct(word)
            if correction != word:
                sys.stderr.write("Correction: %s -> %s\n" % (word, correction))
                self.nbCorrections += 1
            word = correction
                    
        return word


   def _correct(self, word):
        """Finds the best correction for the word, if one can be found.  The
        method tries to correct common OCR errors, wrong accents, and a few 
        other heuristics.
        
        """            
        # OCR errors
        mappings = [("ii", "ll"), ("II", "ll"), ("l", "I"),
                    ("i", "l"), ("I", "l"), ("l", "i"), ("0", "O")]
        
        replaces = []
        for m in mappings:
            matches = re.finditer(r"(?=%s)" % (m[0]), word)
            for match in matches:
                pos = match.start()
                replace = word[:pos] + m[1] + word[pos + len(m[0]):]
                if (self.dictionary.isWord(replace) and 
                    (m != ("l", "I") or pos == 0)):
                    replaces.append(replace)
        if replaces:
            return max(replaces, key=self.dictionary.getFrequency) 
        
        # Wrong accents
        if self.dictionary.no_accents and not self.dictionary.isWord(word):
            return self.dictionary.correctAccents(word)
        
        # correcting errors such as "entertainin" --> "entertaining"
        if word.endswith("in") and self.dictionary.isWord(word + "g"):
            return word + "g"
                  
        return word


class Language:
    """Representation of a "language", with a name, 2- and 3-letters code,
    preferred encoding formats, writing script, and dictionary (only available
    for a subset of languages).
    
    """
             
    def __init__(self, name, scripts):
        """Initialises the language object"""
        
        self.name = name
        self.codes = [] 
        self.dictionary = None
        self.scripts = scripts
        self.encodings = []
        if "arabic" in self.scripts or "hebrew" in self.scripts:
            self.direction = "rtl"
        else:
            self.direction = "ltr"
        if [s for s in self.scripts if s != "latin" and s != "cyrillic" and s != "greek"]:
            self.unicase = True
        else:
            self.unicase = False
            
    def getDictionary(self):
        """Constructs the dictionary for the language."""
        
        if isinstance(self.dictionary, Dictionary):
            return self.dictionary
        elif self.dictionary:
            self.dictionary = Dictionary(self.dictionary)
            return self.dictionary
        return None
    

    def __str__(self):
        """Returns the language name."""
        return self.name
        
    def __repr__(self):
        """Returns the language name."""
        return self.__str__()
   
    def __hash__(self):
        """Returns the hash of the language name."""
        return self.name.__hash__()
   
    def __eq__(self, other):
        """Returns true if other is a language with the same name, false otherwise."""
        
        if isinstance(other, Language):
            return other.name == self.name
        return other == self.name or other in self.codes
    
    
    def getProb(self, text):
        """Returns the probability that the given text is written in the language, 
        using the langid library.
        
        """
        try:
            import langid
        except RuntimeError:
            return
        result = langid.rank(text)
        for pair in result:
            if pair[0] in self.codes:
                return pair[1]
        return 0.0
       

def getLanguage(langcode):
    """Returns the language object given the code. If no language can be found
    with the provided code, raises a RuntimeError".
    
    """
    if langcode in languages.keys():
        content = languages[langcode]
        if isinstance(content, dict):
            lang = Language(content["name"], content["scripts"])
            lang.encodings = content["encodings"]
            lang.codes = content["codes"]
            if "dictionary" in content:
                lang.dictionary = content["dictionary"]
            return lang
        else:
            return getLanguage(content)
    else:
        raise RuntimeError("Cannot find language with code %s" % langcode)

   
class Dictionary():
    """Representation of a dictionary containing a list of words for a given 
    language along with their unigram frequencies. The dictionary is used
    to perform spell-checking of the documents, and correct common errors
    (such as OCR errors and wrong accents).
    
    """
    def __init__(self, dicFile):
        """Creates a new dictionary from a given file.  Each line in the file 
        must contain a word followed by a space or tab and an integer 
        representing the frequency of the word.
        
        """
        sys.stderr.write("Building dictionary from " + dicFile + "\n")
        if not os.path.exists(dicFile):
            raise RuntimeError("Unigrams file " + dicFile + " cannot be found")
        self.dicFile = dicFile
        self.words = collections.defaultdict(int)
        with io.open(dicFile, encoding="utf-8") as dico:
            for l in dico:
                if not l.startswith("%%") and not l.startswith("#"):
                    split = l.split()
                    word = split[0].strip()
                    frequency = int(split[1].strip())
                    self.words[word] = frequency
        
        sys.stderr.write("Total number of words in dictionary: %i\n" % (len(self.words)))
        
        # Creating a non-accented version of the dictionary (only performed if we 
        # can detect accents in the dictionary). 
        self.no_accents = {}
        first_words = list(self.words.keys())[0:100]
        if len(re.findall(r"[\xe8\xe9\xa8\xa9\xa0\xb9]", " ".join(first_words))) > 10:
            sys.stderr.write("Creating unaccented version of dictionary " + dicFile + "\n")
            for w in self.words:
                stripped = strip(w)
                if (stripped not in self.no_accents or 
                    self.words[w] > self.words[self.no_accents[stripped]]):
                    self.no_accents[stripped] = w
      
               
 
    def isWord(self, word):
        """Returns true if the (lowercased) word can be found in the dictionary,
        and false otherwise.
        
        """
        wlow = word.lower()
        return wlow in self.words or re.sub(r"['-]", "", wlow) in self.words
    
    
    def correctAccents(self, word):
        if self.no_accents:
            stripped = strip(word)
            if stripped in self.no_accents:
                return self.no_accents[stripped]
        return word
        
        
    def getWords(self):
        """Returns the (word,frequency) pairs in the dictionary."""
        return self.words
    
  
    def getFrequency(self, word):
        """Returns the frequency of the word in the dictionary."""
        wlow = word.lower()
        if wlow in self.words:
            return self.words[wlow]
        elif re.sub(r"['-]", "", wlow):
            return self.words[re.sub(r"['-]", "", wlow)]
        else:
            return 0


# Equivalence table between specific (German) characters and their ascii encoding
eqTable = {ord('ß'):'ss', ord('ç'):'c', ord('ä'):'ae', ord('ö'):'oe', ord('ü'):'ue'}
    

def strip(word):
    """Strips the word of accents and punctuation."""
    
    word2 = word.translate(eqTable)   
    normalised = unicodedata.normalize('NFKD', word2)       
    stripped = normalised.encode("ascii", "replace").lower().decode("ascii")
    stripped = re.sub(r"[\.,;':\-!]", "", stripped)
    return stripped


  
