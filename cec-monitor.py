# Changement de source:
# cec-ctl
# Received from TV to all (0 to 15): ACTIVE_SOURCE (0x82):
#         phys-addr: 0.0.0.0

#cec-client:
#  making TV (0) the active source
# DEBUG:   [          132278]     >> TV (0) -> Broadcast (F): active source (82)

# Changement de source SUR raspberry:
# cec-ctl
# Received from TV to all (0 to 15): ACTIVE_SOURCE (0x82):
#         phys-addr: 1.0.0.0


# Turn OFF:
# Received from TV to all (0 to 15): STANDBY (0x36)

# Turn ON directly on raspberry:

# Received from TV to all (0 to 15): ROUTING_CHANGE (0x80):
#         orig-phys-addr: 0.0.0.0
#         new-phys-addr: 1.0.0.0

import subprocess
import os
import signal
import re
import threading
import time

def delayed_stop_kodi():
    time.sleep(10) # 10 seconds for test purposes
    # time.sleep(300)  # 5 minutes
    stop_kodi()

def stop_kodi_thread_starting(stop_kodi_timer):
    if stop_kodi_timer is None or not stop_kodi_timer.is_alive():
        stop_kodi_timer = threading.Thread(target=delayed_stop_kodi)
        stop_kodi_timer.start()

def stop_kodi():
    try:
        # Trouver le processus Kodi
        result = subprocess.run(['pgrep', 'kodi'], capture_output=True, text=True, check=True)
        pids = result.stdout.strip().split('\n')

        if pids:
            for pid in pids:
                if pid:  # Vérifiez que le PID n'est pas une chaîne vide
                    # Envoyer un signal SIGTERM pour arrêter Kodi
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"Kodi process {pid} stopped.")
        else:
            print("No Kodi processes found.")
        get_physical_address()
    except subprocess.CalledProcessError as e:
        print(f"Error stopping Kodi: {e}")

def start_kodi(stop_kodi_timer):
    try:
        if stop_kodi_timer is not None and stop_kodi_timer.is_alive():
            print("Cancelling scheduled Kodi stop.")
            stop_kodi_timer.join()  # Wait for the timer thread to finish

        # Vérifier si Kodi est déjà en cours d'exécution
        result = subprocess.run(['pgrep', 'kodi'], capture_output=True, text=True, check=True)
        pid = result.stdout.strip()

        if pid:
            print(f"Kodi is already running with PID {pid}.")
        else:
            # Lancer Kodi
            process = subprocess.Popen(['kodi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            print("Kodi started.")
            return process
    except subprocess.CalledProcessError:
        # Si pgrep ne trouve pas de processus Kodi, lancer Kodi
        process = subprocess.Popen(['kodi'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        print("Kodi started.")
        return process
    except Exception as e:
        print(f"Error starting Kodi: {e}")
        return None

def get_physical_address():
    try:
        # Exécuter la commande cec-ctl
        result = subprocess.run(['sudo', 'cec-ctl', '--record', '--osd-name', 'Kodi'], capture_output=True, text=True, check=True)
        output = result.stdout

        # Utiliser une expression régulière pour extraire la valeur de Physical Address
        match = re.search(r'Physical Address\s+:\s+([\d\.]+)', output)
        if match:
            physical_address = match.group(1)
            return physical_address
        else:
            print("Physical Address not found in the output.")
            return None
    except subprocess.CalledProcessError as e:
        print(f"Error executing cec-ctl: {e}")
        return None

def monitor_cec(physical_address):
    print(f"Monitoring CEC with physical address {physical_address}")
    try:
        # Lancer la commande de monitoring
        process = subprocess.Popen(['sudo', 'cec-ctl', '-m'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        numberOfLinesToTrack = -1
        stop_kodi_timer = None

        # Lire la sortie en temps réel
        for line in process.stdout:
            if numberOfLinesToTrack > 0:
                numberOfLinesToTrack -= 1

            if "from TV to all" in line and "STANDBY" in line:
                print("Received STANDBY command. Stopping Kodi")
                stop_kodi_thread_starting(stop_kodi_timer)
            elif "from TV to all" in line and "ROUTING_CHANGE" in line:
                # Next line will be where TV is actually, and after it will be the destination.
                numberOfLinesToTrack = 2
            elif "from TV to all" in line and "ACTIVE_SOURCE" in line:
                # Next line will be where TV is going.
                numberOfLinesToTrack = 1
            elif numberOfLinesToTrack == 0:
                print(f"Line to track: {line}")
                if physical_address in line:
                    print("Starting Kodi due to active source change")
                    start_kodi(stop_kodi_timer)
                else:
                    print("Stopping Kodi due to active source change")
                    stop_kodi_thread_starting(stop_kodi_timer)
                numberOfLinesToTrack = -1
        # Attendre que le processus se termine
        process.wait()
    except Exception as e:
        print(f"Error monitoring cec-ctl: {e}")

# Appeler la fonction et stocker la valeur dans une variable
physical_address = get_physical_address()
if physical_address:
    print(f"Physical Address: {physical_address}")
    print("Starting Monitoring")
    monitor_thread = threading.Thread(target=monitor_cec, args=(physical_address,))
    monitor_thread.start()
    # Attendre que le thread de monitoring se termine
    monitor_thread.join()
else:
   print("No physical address found.")
