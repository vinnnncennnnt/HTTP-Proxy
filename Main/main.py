import socket
import threading
import re
import json
class Proxy : 
    def __init__ (self):   # initialisation des parametres du proxy 
        self.config = None
        self.loadConfig()

    def loadConfig (self):
        configFile = open('config.json')
        self.config=json.load(configFile)
        configFile.close()
    
    def start(self):  # creer la socket qui communique entre le client et le serveur
        self.serverSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.serverSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.serverSocket.bind((self.config["parameters"]['host'] , self.config["parameters"]['port']))
        self.serverSocket.listen(socket.SOMAXCONN)
        print("[+] Listening on port " , self.config["parameters"]['port'])
        while 1:  # commencer la communication
            conn, addr = self.serverSocket.accept()
            line=conn.recv(self.config["parameters"]['bufferSize'])
            #en fonction des parametres en redirige le client, les premiers fonction pour le parametrage du serveur
            try : 
                url = line.decode('utf_8').split('\n')[0].split(' ')[1]
                thr =None 
                if url == 'http://config/':
                    thr =threading.Thread(target=self.goToConfigure (conn))
                    
                elif url == 'http://config/home':
                    thr =threading.Thread(target=self.showConfigPage (conn))

                elif re.search('(?:https?:\/\/config\/proxySetting\?host=)(?:[-_\.a-zA-Z]+|([0-9]{1,3}[\.]){3}[0-9]{1,3})&(?:port=)[0-9]+&(?:buffSize=)[0-9]+', url):
                    thr =threading.Thread(target=self.setProxyParameters , args=(url , conn ))

                elif re.search('(?:https?:\/\/config\/forbiddenHosts\?host=)(?:[-_\.a-zA-Z]+|([0-9]{1,3}[\.]){3}[0-9]{1,3}).*', url):
                    thr =threading.Thread(target=self.setForbiddenHosts , args=(url , conn))

                elif re.search('(?:https?:\/\/config\/forbiddenExtensions\?Extension=)(?:[\.a-zA-Z]).*', url):
                    thr =threading.Thread(target=self.setForbiddenExtensions , args=(url , conn))
                 
                elif re.search('(?:https?:\/\/config\/redirectHosts\?host=)(?:[-_\.a-zA-Z]+|([0-9]{1,3}[\.]){3}[0-9]{1,3})&(?:redirectTo=)(?:[-_\.a-zA-Z]+|([0-9]{1,3}[\.]){3}[0-9]{1,3}).*', url):
                    thr =threading.Thread(target=self.setRedirectHosts , args=(url , conn))

                elif re.search('(?:https?:\/\/config\/changeWord\?word=).+(?:&changeTo=).+', url):
                    thr =threading.Thread(target=self.setChangeHTMLWord , args=(url , conn))

                else :
                    thr =threading.Thread(target=self.mainThread , args=(line , conn, addr)) # si on es en HTTP et on configure pas le serveur

                thr.setDaemon(True)   
                thr.start()
            except Exception as e :
                conn.close()

    '''
    @Param line : une requete POST et renvoie un tableau de parametres de la requete POST
    '''
    def parseGETRequest (self , line ):
        pos=0
        tab=[]
        subString=''
        start =False
        for i , unChar in enumerate(line) :
            if unChar=='?':
                pos=i
                break
        line = line[pos+1:]+'&'
        for  i ,unChar in enumerate(line ):
            if unChar=='=':
                start = True
            if unChar == "&" :
                start = False
            if start : 
                subString+=unChar
                continue
            if not start  and unChar == "&" :
                tab.append(subString[1:])
                subString=''
                start = False
        return tab
    '''
    @Param : line => l'URL qui contient les parametres
    Les fonctions suivantes lisent le fichier JSON et ajoutent ou supprimment les données
    mot par mot
    '''
    def setChangeHTMLWord(self , line , conn):
        params = self.parseGETRequest(line)
        f = open('config.json')
        configFile = json.load(f)

        # si len(params) > 2 ça veut dire que le checkbox a ete coché , et on supprime de la liste
        if len(params)>2:
            obj = None
            removeWord=False
            word=params[0]
            for val  in configFile['changeWords']:
                if word == val['word']:
                    removeWord=True
                    obj = {"word" : word , "changeTo" : val["changeTo"]}
                    break
            if  removeWord:
                configFile['changeWords'].remove(obj)
        else:
            addWord=False
            for val  in configFile['changeWords']:
                if params[0] == val['word']:
                    addWord=True
                    break

            if not addWord:
                configFile['changeWords'].append({"word" : params[0] , "changeTo" : params[1]})
        with open("config.json", "w") as i :
            json.dump(configFile, i)
        f.close()
        self.showConfigPage(conn)



    def setRedirectHosts (self , line , conn):
        params = self.parseGETRequest(line)
        f = open('config.json')
        configFile = json.load(f)
        try :
            socket.gethostbyname(params[0]) # pour lancer une exception si le host n'est pas valide
            if len(params)>2:
                obj = None
                removeHost=False
                host=params[0]
                for val  in configFile['redirectHosts']:
                    if host == val['host']:
                        removeHost=True
                        obj = {"host" : host , "changeTo" : val["changeTo"]}
                        break
                if  removeHost:
                    configFile['redirectHosts'].remove(obj)
            else:
                addHost=False
                for val  in configFile['redirectHosts']:
                    if params[0] == val['host']:
                        addHost=True
                        break

                if not addHost:
                    configFile['redirectHosts'].append({"host" : params[0] , "changeTo" : params[1]})
        except Exception as e:
            pass

        with open("config.json", "w") as i :
            json.dump(configFile, i)
        f.close()
        self.showConfigPage(conn)

        
    def setForbiddenExtensions(self, line , conn):
        params = self.parseGETRequest(line)
        f = open('config.json')
        configFile = json.load(f)
        try :
            if len(params)>1:
                if params[0]  in configFile['deletedExtension']:
                    configFile['deletedExtension'].remove(params[0])
            else:
                if params[0] not in configFile['deletedExtension']:
                    configFile['deletedExtension'].append(params[0])
        except Exception as e:
            pass
        with open("config.json", "w") as i :
            json.dump(configFile, i)
        f.close()
        self.showConfigPage(conn)


    def setForbiddenHosts(self, line , conn):
        params = self.parseGETRequest(line)
        f = open('config.json')
        configFile = json.load(f)
        try :
            socket.gethostbyname(params[0]) # pour lancer une exception si le host n'est pas valide
            if len(params)>1:
                if params[0]  in configFile['forbiddenHosts']:
                    configFile['forbiddenHosts'].remove(params[0])
            else:
                if params[0] not in configFile['forbiddenHosts']:
                    configFile['forbiddenHosts'].append(params[0])
        except Exception as e:
            pass
        
        with open("config.json", "w") as i :
            json.dump(configFile, i)
        f.close()
        self.showConfigPage(conn)


    def setProxyParameters (self , line , conn):
        f = open('config.json')
        configFile = json.load(f)
        params = self.parseGETRequest(line)
        configFile['parameters']['host']=params[0]
        configFile['parameters']['port']=int(params[1])
        configFile['parameters']['bufferSize']=int(params[2])
        with open("config.json", "w") as i :
            json.dump(configFile, i)
        f.close()
        self.showConfigPage(conn)

    '''
    fonction qui renvoie la page de parametres du serveur proxy 
    '''
    def showConfigPage(self , conn):
        self.loadConfig()
        response ='HTTP/1.0 200 OK\n\n' +"<head>\n" +"    <meta charset=\"UTF-8\">\n" +"    <meta http-equiv=\"X-UA-Compatible\" content=\"IE=edge\">\n" +"    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n" +"    <title>Document</title>\n" +"</head>\n" +"<style>\n" +"    table,\n" +"    th,\n" +"    td {\n" +"        border: 1px solid black;\n" +"    }\n" +"</style>\n" +"\n" +"<body>\n" +"    <h2>Parameters</h2>\n" +"    <table style=\"width:30%\">\n" +"        <tr  bgcolor=\"red\">"
        for val in self.config['parameters'] :
            response += f"<th> {val} </th>\n"
        response += "</tr>\n<tr>"
        for key in self.config['parameters'].values():
            response += f"<th> {key} </th>\n"
        response += "</tr>\n</table></table>\n<br>\n<br>\n<h2>Forbidden Hosts</h2>\n<table style=\"width:30%\">"
        for val in self.config['forbiddenHosts']:
            response+=f"<tr>\n<th>\n{val}</th></tr>\n"
        response+="</table>\n<br>\n<br>\n<h2>Forbidden extension</h2>\n<table style=\"width:30%\">\n"
        for val in self.config['deletedExtension']:
            response+=f"<tr>\n<th>\n{val}</th></tr>\n"
        response+="</table>\n<br>\n<br>\n<h2>Redirected Hosts</h2>\n<table style=\"width:30%\">\n<tr  bgcolor=\"red\"> \n<th >Host</th>\n<th >Change to</th>\n</tr>"
        for i in self.config['redirectHosts']:
            response+='<tr>\n'
            for j in i :
                response+=f"<th>{i[j]}</th>\n"
            response+='</tr>\n'
        response += "</table>\n<br>\n<br>\n<h2>Change word into</h2>\n<table style= \"width:30%\">\n    <tr  bgcolor=\"red\"> \n        <th >Word</th>\n        <th >Change to</th>\n        \n    </tr>"
        for i in self.config['changeWords']:
            response+='<tr>\n'
            for j in i :
                response+=f"<th>{i[j]}</th>\n"
            response+='</tr>\n'
        conn.sendall(response.encode('utf_8'))
        conn.close()

    '''
        Fonction qui lit le contenu de la page HTML et le renvoi au serveur
    '''
    def goToConfigure(self , conn):
        fin = open('config.html')
        content = fin.read()
        fin.close()
        # Send HTTP response
        response = 'HTTP/1.0 200 OK\n\n' + content
        conn.sendall(response.encode())
        conn.close()

    '''
        Fontion qui lit un contenu HTML et prend un tableau de sous chaines a supprimer qui sont des extensions (.png , .JPEG) ...etc
    '''
    def removeExtensions (self , str , extensions):
        try:
            str =str.decode('ISO-8859-1' , errors='ignore')
        except Exception as e:
            print(e)
            return str
        for i in range(len(str)):    # on itère sur la chaine et on cherche tous les extension
            for ext in extensions : # on itère sur les extensions souhaitées
                if str.endswith(ext,0 , i):  # si je trouve une phrase qui se termine par mon extension on cherche le debut du tag 
                    for j in range(i+1 ,-1 ,-1): # on a trouvé la fni on cherche le debut du tag qui commence par ="xxx.png" par exemple
                        if str.startswith('="' ,j , i):
                            str=str.replace(str[j:i], '="')  # on fois on l'a trouvé on le supprime avec ine chaine vide
                            break 
        return str.encode('ISO-8859-1')

    
    '''
    Fonction Principale
    '''
    def mainThread(self  ,line , conn , addr):
        try :
            #extract host domain and port
            decodedLine = line.decode("utf_8")
            url = decodedLine.split("\n")[0].split(' ')[1]
            patern=re.search("https?://", url)
            url = url if patern ==None else url[patern.span()[1]:]
            patern = re.search("[a-zA-Z0-9\._-]+\.?[a-zA-Z0-9]*:?[0-9]{0,5}" , url)
            url=patern.group()
            patern=re.search(":", url)
            port = 80 if patern ==None else int(url[patern.span()[1]:])
            url = url if patern ==None else url[:patern.span()[1]-1]
            #get host and port at the end
            self.connectToDestination( conn ,line , url , port , addr)  # on appel la fonction qui se connect au serveur
            
        except Exception as e:
            print(e)
        
    '''
        Fonction qui se connect au serveur et verifient les parametres
    '''
    def connectToDestination(self  , conn ,data , webHost , webPort , addr):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        isBodyTag=False
        fullResponse =b''
        try:
            # restrict forbiden hosts
            try :
                for forbidenHost in self.config['forbiddenHosts']:
                    if socket.gethostbyname(forbidenHost) == socket.gethostbyname(webHost) :
                        print("[+] Forbidden !! try later")
                        conn.close()
                        return  
            except Exception as e:
                print(e)
            #redirect hosts
            try :        
                for host in self.config['redirectHosts']:
                    if socket.gethostbyname(host['host']) == socket.gethostbyname(webHost) :
                        webHost = host['changeTo']
                        data=data.decode('utf_8').replace(  host['host'] , webHost).encode('utf_8')

            except Exception as e:
                print(e)

            newData = self.modifyRequest(data)
            print("[+] Connecting to server ( ", webHost , " ) on port :" , webPort)
            sock.connect((webHost, webPort))
            sock.settimeout(30)
            sock.sendall(newData)

            while 1:
                rep = sock.recv(self.config["parameters"]['bufferSize'])
                fullResponse+=rep
                if self.config['changeWords'] !=0:
                    rep,isBodyTag = self.changeWordsinHTMLPage(rep , isBodyTag)
                if self.config['deletedExtension'] != 0:
                    rep = self.removeExtensions(rep , self.config['deletedExtension'])
                if not rep:
                    conn.sendall(b'\r\n')
                    break
                conn.sendall(rep)
        except  Exception as e:
            print(e)
            pass
        finally :
            print('[+] Connexion closed' , addr)
            conn.close()

    '''
    Fonction quib modifie le contenu de la page HTML
    '''

    def changeWordsinHTMLPage(self , res , isBodyTAG):
        try:
            val =res.decode('ISO-8859-1' , errors='ignore')
        except Exception as e:
            print(e)
            return res , isBodyTAG
        res = val
        htmlStart = res.find('<body')
        htmlEnd = res.find('</body>')
        if htmlStart == -1 and htmlEnd == -1 and not isBodyTAG:
            return res.encode('ISO-8859-1') , isBodyTAG
        
        if htmlStart != -1:
            isBodyTAG = True
        
        if htmlEnd !=-1:
            isBodyTAG =False

        if htmlStart == -1:
            htmlStart = 0

        if htmlEnd == -1:
            htmlEnd = len(res)
        resStart = res[0:htmlStart]
        resEnd = res[htmlEnd:len(res)]
        resSub = res[htmlStart:htmlEnd]
        for val in self.config['changeWords']:
            resSub = resSub.replace(val['word'], val['changeTo'])
        res = resStart + resSub + resEnd
        return res.encode('ISO-8859-1') , isBodyTAG 

    '''
        Fonction qui modifie le contenu de la requete envoyée par le client
    '''
    def modifyRequest(self,request):
        newLine =''
        lines = request.decode("utf_8").split("\n")
        index = len(lines[0]) -2
        lines[0] =   lines[0][:index]+'0'+lines[0][index+1:]
        isGetRequest = True if  lines[0][0] == 'G' else False
        #Suppprimer le nom de domaine 
        index =0
        for i , char in enumerate(lines[0]):
            if char == '/':
                index+=1
                if  index ==3:
                    tmp = 4 if isGetRequest else 5
                    lines[0] =lines [0][:tmp]+lines[0][i:]
                    break 
        for i  in range (0 , len(lines)) :
            if lines[i]  in ['Connection: keep-alive\r' , 'Accept-Encoding: gzip, deflate\r' , 'Proxy-Connection: keep-alive\r' , 'Proxy-Connection: Keep-Alive\r' ] :
                continue
            newLine += lines[i]+ '\n'
        return  newLine[:-1].encode('utf_8')



if __name__ == "__main__":
        proxy = Proxy ()
        proxy.start()