import time
from heartbeat import write_heartbeat

def run():
    offset = 0

    while True:
        print("Bot running... writing heartbeat")
        write_heartbeat(offset)
        offset += 1
        time.sleep(30)

if __name__ == "__main__":
    run()