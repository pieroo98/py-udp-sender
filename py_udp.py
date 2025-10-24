import socket, time, sys, threading

IP       = "192.168.2.3"   # destinazione
PORT     = 5005              # porta destinazione
PAYLOAD  = b"c"*1470           # payload (bytes)
INTERVAL = 0              # secondi tra pacchetti
COUNT    = 0                 # 0 = infinito, >0 = numero pacchetti

sent_bytes = 0
recv_bytes = 0
stop_flag  = False

def receiver(sock):
    global recv_bytes, stop_flag
    sock.settimeout(1)
    while not stop_flag:
        try:
            data, _ = sock.recvfrom(65535)
            recv_bytes += len(data)
        except socket.timeout:
            pass
        except Exception:
            break

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.bind(("", PORT))  # riceve anche sulla stessa porta locale
threading.Thread(target=receiver, args=(s,), daemon=True).start()

sent = 0
start = time.time()

try:
    while True:
        s.sendto(PAYLOAD, (IP, PORT))
        sent += 1
        sent_bytes += len(PAYLOAD)
        now = time.time()
        elapsed = now - start
        if elapsed >= 1.0:  # aggiorna ogni secondo
            mbps_out = (sent_bytes * 8) / 1_000_000 / elapsed
            mbps_in  = (recv_bytes * 8) / 1_000_000 / elapsed
            print(f"TX: {mbps_out:.2f} Mbit/s | RX: {mbps_in:.2f} Mbit/s")
            sent_bytes = recv_bytes = 0
            start = now
        if COUNT and sent >= COUNT:
            break
        time.sleep(INTERVAL)
except KeyboardInterrupt:
    print("\nInterrotto dall'utente.")
finally:
    stop_flag = True
    s.close()
    print(f"Socket chiuso. Pacchetti inviati: {sent}")
