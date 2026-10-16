import paramiko
import time

def start_logging():
    print("Connecting to laptop via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('192.168.1.131', username='noehs', password='noehs')

    print("Deploying Wi-Fi logger script...")
    logger_script = """
cat << 'EOF' > /home/noehs/wifi_logger.sh
#!/bin/bash
echo "Starting Wi-Fi logging. Monitoring nearby networks..." > /home/noehs/wifi_log.txt
while true; do
    echo "--- $(date) ---" >> /home/noehs/wifi_log.txt
    # Use nmcli to list all networks, grep out empty SSIDs
    nmcli -t -f SSID,SIGNAL,SECURITY dev wifi list | grep -v '^:' >> /home/noehs/wifi_log.txt
    sleep 15
done
EOF
chmod +x /home/noehs/wifi_logger.sh
killall wifi_logger.sh 2>/dev/null
nohup /home/noehs/wifi_logger.sh > /dev/null 2>&1 &
echo "Script deployed and running in background!"
"""

    stdin, stdout, stderr = ssh.exec_command(logger_script)
    print(stdout.read().decode())
    err = stderr.read().decode()
    if err:
        print("Stderr:", err)
        
    ssh.close()
    print("Successfully started Wi-Fi logger on 192.168.1.131!")

if __name__ == "__main__":
    start_logging()
