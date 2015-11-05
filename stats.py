
import tarfile, re, srt2xml, sys, fcntl, json, os

statfile = "/cluster/home/plison/mt/tasks/stats.json"

class ArchiveCounter():
    
    def __init__(self, archivePath):
        self.aFile = tarfile.open(archivePath, 'r:gz')
        members = self.aFile.getmembers()
        self.sentences = 0
        self.tokens = 0
        self.corrections = 0
        self.materials = set()
        self.unknowns = 0
        self.duration = 0
        self.encodings = {}
        self.blocks = 0
        self.outliers = []
        self.ratings = {"<-10":0, "-10:0":0, "0":0, "0:10":0, ">10":0}
        self.cds = {"1/1":0, "n/n":0, "incomplete":0}
        self.confidences = {"0":0, "<0.99":0, "1":0}
        self.nbFiles = 0
        print ("Finished extracting archive members (size: %i)"%len(members))
        
        
    def doCounting(self):
        for m in self.aFile.getmembers():
            fd = self.aFile.extractfile(m)
            fd.seek((m.size-1500) if m.size > 1500 else 0)
            fd.readline()
            self.materials.add(os.path.dirname(m.name))
            self.nbFiles += 1
     #       print ("Reading " + m.name)
            foundMeta = False
            for l in fd:
                try:
                    l = l.decode("utf-8")
                except UnicodeError:
                    print("Problem with line " + str(l) + " in " + str(m.name))
                    continue
                if re.search("<meta>",l):
                    foundMeta = True
                match = re.search("<sentences>(\d+)</sentences>",l)
                if match and match.group(1):
                    self.sentences += int(match.group(1))
                match = re.search("<tokens>(\d+)</tokens>",l)
                if match and match.group(1):
                    self.tokens += int(match.group(1))
                match = re.search("<corrected_words>(\d+)</corrected_words>",l)
                if match and match.group(1):
                    self.corrections += int(match.group(1))
                match = re.search("<unknown_words>(\d+)</unknown_words>",l)
                if match and match.group(1):
                    self.unknowns += int(match.group(1))
                match = re.search("<duration>(\d+:\d+:\d+\,?\d*)</duration>",l)
                if match and match.group(1):
                    dur = srt2xml.tosecs(match.group(1))
                    if dur > 0 and dur < 40000:
                        self.duration += dur 
                    else:
                        self.outliers.append(m.name)
                match = re.search("<blocks>(\d+)</blocks>",l)
                if match and match.group(1):
                    self.blocks += int(match.group(1))
                match = re.search("<confidence>(\d+(?:\.\d+))</confidence>",l)
                if match and match.group(1):
                    confidence = float(match.group(1))
                    if abs(confidence) < 0.01:
                       self.confidences["0"] += 1
                    elif abs(confidence) < 0.989:
                       self.confidences["<0.99"] += 1
                    else:
                        self.confidences["1"] += 1
                match = re.search("<rating>(\-?\d+(?:\.\d+))</rating>",l)
                if match and match.group(1):
                    rating = float(match.group(1))
                    if rating < -10:
                        self.ratings["<-10"] += 1
                    elif rating < 0:
                        self.ratings["-10:0"] += 1
                    elif abs(rating) < 0.01:
                        self.ratings["0"] += 1
                    elif rating < 10:
                        self.ratings["0:10"] += 1
                    else:
                        self.ratings[">10"] += 1      
                match = re.search("<encoding>(.+)</encoding>",l)
                if match and match.group(1):
                    encoding = match.group(1)
                    if encoding not in self.encodings:
                        self.encodings[encoding] = 0
                    self.encodings[encoding] += 1
                match = re.search("<cds>(.+)</cds>",l)
                if match and match.group(1):
                    cds = match.group(1)
                    if cds == "1/1":
                        self.cds["1/1"] += 1
                    elif re.match(r"(\d+)/(\1)", match.group(1)):
                        self.cds["n/n"] += 1
                    else:
                        self.cds["incomplete"] += 1
            if not foundMeta:
                print("<meta> tag was not found in %s"%m.name)
            
                    
    
    def __str__(self):

        return str(self.todic())
        
    def todic(self):
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        duration = "%02d:%02d:"%(h,m) + ("%.0f"%s).replace(".",",")

        return {"sentences":self.sentences, "tokens":self.tokens,
                "corrections":self.corrections, "unknowns":self.unknowns,
                "duration":duration, "files":self.nbFiles,
                "encodings":self.encodings, "blocks":self.blocks,
                "ratings":self.ratings, "cds":self.cds, 
                "confidences":self.confidences, "materials":len(self.materials),
                "outliers":self.outliers[:10]}
        
    
    def writeStats(self):
        currenttext = open(statfile).read() if os.path.exists(statfile) else "{}"
        dic = json.loads(currenttext)
        lang = re.match("(\w+)[\-\.].+", os.path.basename(self.aFile.name)).group(1)
        dic[lang] = self.todic() 
        with open(statfile, 'w') as g:
            fcntl.flock(g, fcntl.LOCK_EX)
            g.write(json.dumps(dic, indent=4, sort_keys=True))
            fcntl.flock(g, fcntl.LOCK_UN)
        

langs = ['afr', 'alb', 'ara', 'arm', 'baq', 'ben', 'bos', 'bre', 'bul', 
         'cat', 'chi', 'cze', 'dan', 'dut', 'ell', 'epo', 'est', 
         'fin', 'fre', 'geo', 'ger', 'glg', 'heb', 'hin', 'hrv', 'hun', 
         'ice', 'ind', 'ita', 'jpn', 'kor', 'lav', 'lit', 'mac', 'mal', 
         'may', 'nor', 'per', 'pob', 'pol', 'por', 'rum', 'rus', 
         'sin', 'slo', 'slv', 'spa', 'swe', 'tam', 'tel', 'tgl', 'tha', 
         'tur', 'ukr', 'urd', 'vie', 'zhe_zh', 'zhe_en', 'zht', 'scc', 'eng']  
        
if __name__ == '__main__':

    for l in langs:
        print("Working on language: " + l)
        counter = ArchiveCounter("../data/opensubs2015/" + l + "-raw.tar.gz")
        counter.doCounting()
        print("Result: " + str(counter))
        counter.writeStats()
    
             