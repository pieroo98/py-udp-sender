import socket

IP   = "0.0.0.0"       # ascolta su tutte le interfacce
PORT = 5005            # stessa porta dello STM

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((IP, PORT))

print(f"Listening on {IP}:{PORT}")

while True:
    data, addr = sock.recvfrom(2048)
    print(f"RX {len(data)} bytes from {addr[0]}:{addr[1]} -> {data.hex(' ')}")
    # opzionale: echo back
    # sock.sendto(data, addr)
