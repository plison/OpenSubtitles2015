
import tarfile, re, srt2xml, sys, fcntl, json, os


class TextExtractor():
    
    def __init__(self, archivePath):
        self.aFile = tarfile.open(archivePath, 'r:gz')
        members = self.aFile.getmembers()
        print ("Finished extracting archive members (size: %i)"%len(members))
        
        
    def doWriting(self):
        for m in self.aFile.getmembers():
            
                    
        
    def todic(self):
        m, s = divmod(self.duration, 60)
        h, m = divmod(m, 60)
        duration = "%02d:%02d:"%(h,m) + ("%.0f"%s).replace(".",",")

        return {"sentences":self.sentences, "tokens":self.tokens,
                "corrections":self.corrections, "unknowns":self.unknowns,
                "duration":duration, "files":self.nbFiles,
                "encodings":self.encodings, "blocks":self.blocks,
                "ratings":self.ratings, "cds":self.cds, 
                "confidences":self.confidences, "materials":len(self.materials)}
        
    
    def writeStats(self):
        currenttext = open(statfile).read() if os.path.exists(statfile) else "{}"
        dic = json.loads(currenttext)
        lang = re.match("(\w+)[\-\.].+", os.path.basename(self.aFile.name)).group(1)
        dic[lang] = self.todic() 
        with open(statfile, 'w') as g:
            fcntl.flock(g, fcntl.LOCK_EX)
            g.write(json.dumps(dic, indent=4, sort_keys=True))
            fcntl.flock(g, fcntl.LOCK_UN)
        

if __name__ == '__main__':

    counter = ArchiveCounter(sys.argv[1])
    counter.doCounting()
    print("Result: " + str(counter))
    counter.writeStats()

             