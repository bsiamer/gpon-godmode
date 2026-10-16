import pty
import os
import sys
import time

def ssh_command(user, host, password, command):
    pid, fd = pty.fork()
    if pid == 0:
        # Child process: execute ssh
        os.execvp("ssh", ["ssh", "-o", "StrictHostKeyChecking=no", f"{user}@{host}", command])
    else:
        # Parent process: interact with ssh
        try:
            output = b""
            # Read until password prompt
            while b"password:" not in output.lower():
                try:
                    chunk = os.read(fd, 1024)
                    if not chunk: break
                    output += chunk
                except OSError:
                    break
            
            # Send password
            os.write(fd, (password + "\n").encode())
            time.sleep(2)
            
            # Read remaining output
            while True:
                try:
                    chunk = os.read(fd, 4096)
                    if not chunk: break
                    output += chunk
                except OSError:
                    break
            print(output.decode(errors='ignore'))
        except Exception as e:
            print("Error:", e)
        finally:
            try:
                os.waitpid(pid, 0)
            except ChildProcessError:
                pass

script = """
cat << 'EOF' > /home/noehs/wifi_logger.sh
#!/bin/bash
echo "Starting Wi-Fi logging. Monitoring nearby networks..." > /home/noehs/wifi_log.txt
while true; do
    echo "--- $(date) ---" >> /home/noehs/wifi_log.txt
    nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list | grep -v '^:' >> /home/noehs/wifi_log.txt
    sleep 15
done
EOF
chmod +x /home/noehs/wifi_logger.sh
killall wifi_logger.sh 2>/dev/null
nohup /home/noehs/wifi_logger.sh > /dev/null 2>&1 &
echo "Script deployed and running in background!"
"""

print("Deploying via pty ssh...")
ssh_command('noehs', '192.168.1.131', 'noehs', script)
