
import gzip,tarfile,re,os,sys,io,tarfile,time,collections,uuid,subprocess
from io import BytesIO
from gzip import GzipFile
from tarfile import TarInfo
import xml.etree.ElementTree as et
import utils as utils
from srt2xml import SubtitleConverter

exportFile = "/projects/researchers/researchers01/plison/data/export_all.txt"
infoFile = "/projects/researchers/researchers01/plison/data/subtitles_all.txt"
omdbFile = "/projects/researchers/researchers01/plison/data/omdb.txt"
ratingFile = "/projects/researchers/researchers01/plison/data/sub_attributes.csv"
sub2srt = os.path.dirname(os.path.abspath(__file__)) + "/sub2srt.pl"
ssa2srt = os.path.dirname(os.path.abspath(__file__)) + "/ssa2srt.pl"

class Subtitle:
    
    def __init__(self, subid, imdb, langcode, format, numcds, date, year):
        self.subid = subid
        self.imdb = imdb
        self.langcode = langcode
        self.subformat = format
        self.fps = None
        self.files = [None]*numcds
        self.year = year if year else "unknown"
        self.meta = {"source":{},"subtitle":{"date":date},"id":subid}
        
            
    def addFilePointer(self, fileid, cdnum, fd, offset, size):
        self.files[cdnum-1] = (fileid, fd, offset, size)
   
    def getFileObjects(self):
        inputs = []
        for f in self.files:
            if f:
                fileid, fd, offset,size = f    
                fd.seek(offset,0)
                content = BytesIO(fd.read(size))
                input = GzipFile(fileid,'rb',fileobj=content)
                if self.subformat == "ssa":
                    input = self.convertFromSsa(input)
                elif self.subformat != "srt":
                    input = self.convertFromSub(input)
                input.contentsize=size
                inputs.append(input) 
        return inputs
    
     
    def __eq__(self, other):
        if hasattr(other,"subid"):
            return self.subid == other.subid
        return False


    def convertFromSsa(self, gzipfile):
        sys.stderr.write("Converting subtitle from ssa to srt\n")
        binaryContent= gzipfile.read()
        tempfile = "/tmp/" + str(uuid.uuid4()) + ".sub"
        fd = open(tempfile, 'wb')                   
        fd.write(binaryContent)        
        fd.close()
 
        p = subprocess.Popen(ssa2srt + " " + tempfile, shell=True, stdout=subprocess.PIPE)
        stdout, stderr = p.communicate()
        os.remove(tempfile)
        try:
            p.terminate()
        except:
            pass
        return BytesIO(stdout)
    
    
    def convertFromSub(self,gzipfile):
        sys.stderr.write("Converting subitle from sub to srt\n")
        binaryContent= gzipfile.read()
        tempfile = "/tmp/" + str(uuid.uuid4()) + ".sub"
        fd = open(tempfile, 'wb')                   
        fd.write(binaryContent)        
        fd.close()

        tempfile2 = "/tmp/" + str(uuid.uuid4()) + ".srt"
        cmd = "%s %s %s"%(sub2srt,tempfile, tempfile2)
        cmd += " --fps=%f"%self.fps if self.fps else ""

        lang = utils.getLanguage(self.langcode)
        encoding = lang.encodings[1] if len(lang.encodings) > 1 else "utf-8"
        cmd += " --fenc=" + encoding 
        
        subprocess.call(cmd, shell=True)
        if not os.path.exists(tempfile2) or os.stat(tempfile2).st_size < 100:
            raise RuntimeError("Conversion of %s to srt failed"%self.subformat)            
        fd = open(tempfile2, 'rb')
        content = fd.read()
        fd.close()
        os.remove(tempfile)
        os.remove(tempfile2)
        
        return BytesIO(content)




def getSubtitles(langcode, nbPartitions, part):
            
    subtitles = extractSubtitles()
    subtitles_list = {}
    for lang in subtitles:
        subtitles_list[lang] =  list(subtitles[lang].values())
    langcode2 = utils.getLanguage(langcode).codes[1]
    nbSubtitles = len(subtitles_list[langcode2])
    partlength = int(nbSubtitles/nbPartitions)
    partstart = (part-1)*partlength
    partend = part*partlength if part < nbPartitions else nbSubtitles

    sublist = subtitles_list[langcode2][partstart:partend]
    
    subtitles_subset = {s.subid:s for s in sublist}
    return subtitles_subset


def extractSubtitles():
    
    subtitles = {}
    fd = open(infoFile, 'r')
    fd.readline()
    for line in fd:
        split = line.split('\t')
        if len(split) == 16:
            subid = split[0]
            year = split[2]
            langcode = split[4]
            imdb = split[6]
            subformat = split[7]
            sumcds = int(split[8])
            date = split[5].split(" ")[0]
            sub = Subtitle(subid, imdb, langcode, subformat, sumcds,date, year)
            if split[10]:
                sub.fps = float(split[10])
            if langcode not in subtitles:
                subtitles[langcode] = {}
            subtitles[langcode][subid] = sub
    fd.close()
    
    return subtitles



def addFilePointers(subset, archive):
        
    export = open(exportFile, 'r')
    files = {}
    cdproblems = 0
    for l in export:
        split = l.rstrip().split('\t')
        if len(split)>=6:
            subid = split[3]
            fileid = split[1]
            if fileid and split[4]:
                cdnum = int(split[4])
                if subid in subset:
                    if cdnum < 1 or cdnum > len(subset[subid].files):
                        cdproblems += 1
                        continue
                    files[fileid] = (subid,cdnum)
    sys.stderr.write("Number of discarded subtitles: %i\n"%cdproblems)    
    export.close()
    
    fdtar = tarfile.open(archive, mode='r')
    fdbin = open(archive, mode='rb')
    for subfile in fdtar:
        fileId = os.path.basename(subfile.name).split(".")[0]
        if fileId in files:
            subid, cdnum = files[fileId]
            if subid in subset:
                sub = subset[subid]
                offset,size = subfile.offset_data, subfile.size
                sub.addFilePointer(fileId, cdnum, fdbin, offset, size)
    fdtar.close()
   

def addNumCds(subset):
    
    for sub in subset.values():
        numactual = len([x for x in sub.files if x])
        numtotal = len(sub.files)
        sub.meta["subtitle"]["cds"] = "%i/%i"%(numactual,numtotal)
        if numactual != numtotal:
            cdlist = [str(i+1) for i in range(0,numtotal) if sub.files[i]]
            sub.meta["subtitle"]["cds"] += " (%s)"%(",".join(cdlist))
 
         

def addOmdbInfo(subset):   
    imdbs = {}
    for sub in subset.values():
        imdb = sub.imdb
        if imdb not in imdbs:
            imdbs[imdb] = [sub]
        else:
            imdbs[imdb].append(sub)
            
    fd = open(omdbFile, 'r', encoding="latin-1")
    fd.readline()
    for line in fd:
        split = line.split('\t')
        imdb = split[0]
        if imdb in imdbs:
            for sub in imdbs[imdb]:
                sub.meta["source"]["year"]=split[3]
                sub.meta["source"]["duration"]=split[5]
                sub.meta["source"]["genre"]=split[6]
                sub.meta["source"]["original"]=split[17]
                sub.meta["source"]["country"]=split[18]
    fd.close()
                


def addRatingInfo(subset):   

    fd = open(ratingFile, 'r')
    for line in fd:
        split = line.split(',')
        subId = split[0].strip("\"")
        if subId in subset:
            sub = subset[subId]    
            nbBad = int(split[1].strip("\""))
            avgScore = float(split[2].strip("\""))
            nbVotes = int(split[3].strip("\""))
            member = split[4].strip("\"")
            rating = (-10 * nbBad) + ((avgScore-5) * nbVotes)
            rating += 2 if member=="trusted" or member=="subtranslator" else 0
            sub.meta["subtitle"]["rating"] = str(rating)
    fd.close()

   

def _addToArchive(output, filename, archive):
    output.seek(0)
    xmlInfo = TarInfo(filename)
    xmlInfo.size = len(output.getbuffer())
    xmlInfo.mtime = time.time()
    archive.addfile(xmlInfo,output)    
    output.close()
    
    
def splitBilingual(archive):
    sys.stderr.write("Splitting " + archive + " into the 2 languages\n")
    archive = tarfile.open(archive, 'r')
    archive1 = tarfile.open(archive.name.replace(".tar", "1.tar"), 'w')
    archive2 = tarfile.open(archive.name.replace(".tar", "2.tar"), 'w')
    for member in archive.getmembers():
        f = archive.extractfile(member)
        sys.stderr.write("Splitting file %s\n"%f.name)
        fs = [BytesIO(),BytesIO()]
        sids = [1,1]
        current = fs
        for l in f:
            l = l.decode("utf-8")
            match = re.search("<s\sid\=\"\d+\"\slang\=\"(\d)\">",l)
            if match:
                langnum = 0 if match.group(1)=="1" else 1
                l = re.sub("id\=\"\d+\"", "id=\"%s\""%sids[langnum],l)
                current = [fs[langnum]]
                sids[langnum] += 1
            for c in current:
               c.write(l.encode("utf-8")) 
            if re.search("<\/s>",l):
                current = fs
        _addToArchive(fs[0], member.name, archive1)
        _addToArchive(fs[1], member.name, archive2)
    archive1.close()
    archive2.close()
    
                
def convertArchive(archiveFile, outputFile, langcode=None, encoding=None, 
                   alwaysSplit=False, rawOutput=None, nbPartitions=1, part=1):
    
    if not langcode:
        langcode = re.search(r'([^/]+)\.tar',archiveFile).group(1)
    language = utils.getLanguage(langcode)  

    sys.stderr.write("Reading the subtitle table...\n")
    subset = getSubtitles(langcode,nbPartitions,part)
    sys.stderr.write("Finished reading the subtitle table.\n")
    sys.stderr.write("Reading the export and archive file...\n")
    addFilePointers(subset, archiveFile)
    sys.stderr.write("Finished reading the archive file.\n")
    sys.stderr.write("Reading the additional databases...\n")
    addNumCds(subset)
    addOmdbInfo(subset)
    addRatingInfo(subset)
    sys.stderr.write("Finished reading the databases.\n")

    nbSubtitles = sum([len([f for f in s.files if f]) for s in subset.values()])
    sys.stderr.write("--> Processing %i subtitles (language: %s)\n" 
                     %(nbSubtitles,language.name))
         
    outputFile = tarfile.open(outputFile, mode='w')
    if rawOutput:
        rawOutputFile = tarfile.open(rawOutput, mode='w')
        
    for sub in subset.values():        
            
        srtFiles = ", ".join([s[0]+"."+sub.subformat for s in sub.files if s])
        if not srtFiles:
            sys.stderr.write(sub.subid + " not in archive\n")
            continue
        path = sub.year + "/" + sub.imdb + "/" + sub.subid + ".xml"
        sys.stderr.write("Processing %s (output file: %s)\n"%(srtFiles, path))
        output = BytesIO()
        routput = BytesIO() if rawOutput else None

        try:
            input = sub.getFileObjects()                
        except:
            sys.stderr.write("Conversion problem: %s\n"%sys.exc_info()[1])
            continue       
        try:
            converter = SubtitleConverter(input,output,routput,language,sub.meta)
            converter.doConversion()
            _addToArchive(output,path,outputFile)
            if rawOutput:
                _addToArchive(routput,path,rawOutputFile)
        except KeyboardInterrupt:
            break
        except:
            sys.stderr.write("Processing error: %s\n"%sys.exc_info()[1])
        for i in input:
            i.close()
        output.close()
        if rawOutput:
            routput.close()

    outputFile.close() 
    if rawOutput:
        rawOutputFile.close() 
       
 

if __name__ == '__main__':
    
    import argparse
 
    cmdOptions = argparse.ArgumentParser(prog="tar2xml")
    cmdOptions.add_argument("archiveFile", 
                               help="Path to the archive file in tar format")
    cmdOptions.add_argument("outputFile", 
                          help="""Path to the archive output file. If omitted, 
                          writes to the standard output""")
    cmdOptions.add_argument("-r", dest="rawOutput", 
                          help="raw output file (without tokenization)")
    cmdOptions.add_argument("-l", dest="langcode", help="language code (ISO-639-3)")
    cmdOptions.add_argument("-e",dest="encoding",  
                          help="text encoding for the srt-file (if omitted, try to detect automatically)")
    cmdOptions.add_argument("-s", dest="alwaysSplit", action='store_true', 
                          help="always start a new sentence at new time frames (default is false)")
    cmdOptions.add_argument("-n", dest="nbPartitions", default=1,type=int,
                            help="Number of partitions for processing the archive file")
    cmdOptions.add_argument("-p", dest="part", default=1, type=int,
                            help="Part to process in the partitioned archive")


    args = vars(cmdOptions.parse_args())

    convertArchive(**args)  
    
    
    
   
        
        