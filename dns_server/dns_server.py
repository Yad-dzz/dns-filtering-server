import socket
from dnslib import DNSRecord, QTYPE, RR, A
from flask import Flask, request
import threading

# Fonction de scraping (simulée : retourne toujours True pour bloquer les sites)
def analyse_site(url):
    print(f"Analyse du site : {url}")
    return True  # Toujours considérer le site comme malveillant

# Serveur DNS
class DNSServer:
    def __init__(self, host='0.0.0.0', port=53):
        self.host = host
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.host, self.port))

    def handle_request(self, data, addr):
        request = DNSRecord.parse(data)
        qname = str(request.q.qname)

        print(f"Requête reçue pour {qname}")  # Ajout du log

        response = request.reply()
        
        if analyse_site(qname):
            print(f"{qname} est bloqué !")
            response.add_answer(RR(qname, QTYPE.A, rdata=A("0.0.0.0")))
        else:
            print(f"{qname} est autorisé.")

        self.sock.sendto(response.pack(), addr)

    def run(self):
        print(f"Serveur DNS en écoute sur {self.host}:{self.port}")
        while True:
            data, addr = self.sock.recvfrom(512)
            self.handle_request(data, addr)

# Lancement du serveur DNS
def start_dns_server():
    server = DNSServer()
    server.run()

# API Web pour test (Flask)
app = Flask(__name__)

@app.route('/test', methods=['GET'])
def test():
    url = request.args.get('url', '')
    if analyse_site(url):
        return {"status": "bloqué", "url": url}, 403
    return {"status": "autorisé", "url": url}, 200

if __name__ == "__main__":
    threading.Thread(target=start_dns_server, daemon=True).start()
    app.run(host='0.0.0.0', port=5000)
