import socket
import time
import struct
import threading

IP       = "192.168.2.3"
PORT     = 5005
PAYLOAD_SIZE = 1472
TARGET_MBPS  = 60  # Mbps target
COUNT    = 0   # 0 = infinito

HEADER_FMT = "!Id"  # seq(uint32) + timestamp(double)
HEADER_SIZE = struct.calcsize(HEADER_FMT)

DATA_SIZE = PAYLOAD_SIZE - HEADER_SIZE
DATA = b"c" * DATA_SIZE

# Intervallo target tra pacchetti (secondi)
# pacchetti/s = 100_000_000 / (PAYLOAD_SIZE * 8)
TARGET_PPS      = (TARGET_MBPS * 1_000_000) / (PAYLOAD_SIZE * 8)
TARGET_INTERVAL = 1.0 / TARGET_PPS  # ~0.0001178 s ≈ 117.8 µs

sent_bytes = 0
recv_bytes = 0
recv_packets = 0
lost_packets = 0

last_seq = -1
jitter = 0
last_transit = None

stop_flag = False


# ================= RECEIVER =================
def receiver(sock):
    global recv_bytes, recv_packets
    global lost_packets, last_seq
    global jitter, last_transit, stop_flag

    sock.settimeout(1)

    while not stop_flag:
        try:
            data, _ = sock.recvfrom(65535)
            recv_time = time.time()

            if len(data) < HEADER_SIZE:
                continue

            seq, send_ts = struct.unpack(HEADER_FMT, data[:HEADER_SIZE])

            recv_packets += 1
            recv_bytes += len(data)

            if last_seq >= 0 and seq > last_seq + 1:
                lost_packets += seq - last_seq - 1
            last_seq = seq

            transit = recv_time - send_ts
            if last_transit is not None:
                d = abs(transit - last_transit)
                jitter += (d - jitter) / 16
            last_transit = transit

        except socket.timeout:
            pass
        except Exception:
            break


# ================= SOCKET =================
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("", PORT))

threading.Thread(target=receiver, args=(sock,), daemon=True).start()


# ================= SENDER =================
seq = 0
start = time.time()
sent_packets = 0

print(f"Target: {TARGET_MBPS} Mbps → {TARGET_PPS:.0f} pps, intervallo {TARGET_INTERVAL*1e6:.1f} µs")

try:
    next_send = time.perf_counter()

    while True:
        # Busy-wait preciso per rispettare l'intervallo target
        while time.perf_counter() < next_send:
            pass

        timestamp = time.time()
        header = struct.pack(HEADER_FMT, seq, timestamp)
        packet = header + DATA

        sock.sendto(packet, (IP, PORT))

        sent_packets += 1
        sent_bytes += len(packet)
        seq += 1
        next_send += TARGET_INTERVAL  # scheduling assoluto, evita deriva

        now = time.time()
        elapsed = now - start

        if elapsed >= 1.0:
            mbps_tx = (sent_bytes * 8) / 1e6 / elapsed
            mbps_rx = (recv_bytes * 8) / 1e6 / elapsed
            pps_tx = sent_packets / elapsed
            pps_rx = recv_packets / elapsed
            total_expected = recv_packets + lost_packets
            loss_pct = (lost_packets / total_expected * 100) if total_expected else 0

            print(
                f"TX {mbps_tx:.2f} Mbps ({pps_tx:.0f} pps) | "
                f"RX {mbps_rx:.2f} Mbps ({pps_rx:.0f} pps) | "
                f"Loss {loss_pct:.2f}% | "
                f"Jitter {jitter*1000:.3f} ms"
            )

            sent_bytes = 0
            recv_bytes = 0
            recv_packets = 0
            sent_packets = 0
            lost_packets = 0
            start = now

        if COUNT and seq >= COUNT:
            break

except KeyboardInterrupt:
    print("\nInterrotto")

finally:
    stop_flag = True
    sock.close()
    print("Socket chiuso")