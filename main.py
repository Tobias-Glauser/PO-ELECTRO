import time
import serial
import RPi.GPIO as GPIO
import requests
import smbus
import threading
import atexit
from timerV2 import RepeatedTimer
from qrreader import QRReader
from serial.tools import list_ports
# from machine import Timer

jelastic_api = 'https://voiture.divtec.me/api/'
obs_api = 'http://192.168.1.100/obs/'

#					Initialisation UART pour le chrono

uart_chrono = serial.Serial('/dev/ttyAMA0', 9600, parity=serial.PARITY_NONE,
  stopbits=serial.STOPBITS_ONE,
  bytesize=serial.EIGHTBITS,
  timeout=1)

#                   Données à transférer
dictionary = {
    "query_id": None,
    "race_finish": None,
    "sector1": None,
    "sector2": None,
    "race_start": None,
    "speed": None
}

authentification = {
    "section": "race",
    "password": "Ch10r3.0d1n3tt3?G1@Ut0b_1nF$G@3tM1c!G1g@Ju1_313c",
    "token": None
}

#					Variables
old_qr = None
pause = 0
run = 0
fin = 0
timer_fin = 0
StartTick = 0
StartTime = 0
StopTick = 0
interrupt_Start = 0
interrupt_Stop = 0
interrupt_Sect1 = 0
interrupt_Sect2 = 0
capteur_vitesse_1 = 0
capteur_vitesse_2 = 0
TotalTime = 0
actualTick = 0
actualTime = 0
timer_pause = 0
time_capt_vit_1 = 0
soft_timer = None
GPIO.setmode(GPIO.BCM)
S1 = 26#start
S2 = 0#stop
S3 = 6#sect1
S4 = 5#sect2
S5 = 19#catp1
S6 = 13#capt2

start_barrier = 21#signal barrier start
capt1_barrier = 20#signal barrier capt1
capt2_barrier = 16#signal barrier capt2
sect1_barrier = 12#signal barrier sect1
sect2_barrier = 1#signal barrier sect2
stop_barrier = 7#signal barrier stop
bonus_elt_out = 8
bonus_dcm_out = 25
bonus_aut_out = 24
bonus_mmc_out = 23
signal_run =18
signal_souffleuse = 17

GPIO.setup(start_barrier, GPIO.OUT)
GPIO.setup(capt1_barrier, GPIO.OUT)
GPIO.setup(capt2_barrier, GPIO.OUT)
GPIO.setup(sect1_barrier, GPIO.OUT)
GPIO.setup(sect2_barrier, GPIO.OUT)
GPIO.setup(stop_barrier, GPIO.OUT)
GPIO.setup(bonus_elt_out, GPIO.OUT)
GPIO.setup(bonus_dcm_out, GPIO.OUT)
GPIO.setup(bonus_aut_out, GPIO.OUT)
GPIO.setup(bonus_mmc_out, GPIO.OUT)
GPIO.setup(signal_run, GPIO.OUT)
GPIO.setup(signal_souffleuse, GPIO.OUT)

GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S5, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
Query_ID = None
penalitee = 0#En milliseconds
temps_final = 0
distance = 50#distance en mm entre les deux capteurs pour la vitesse

res = requests.post(jelastic_api + "authentication/section/", json=authentification)
print(res.json())
authentification["token"] = res.json()["token"]
print(authentification["token"])
token_str = "Bearer " + str(authentification["token"])
print(token_str)


#					Timers
def runtime_handler():  # Timer 10ms
    global uart_chrono, actualTick, actualTime, StartTick
    actualTick = time.perf_counter_ns()
    actualTime = (actualTick - StartTick) // 10000000
    # print (str(actualTime))


def runtime_handler_chrono():  # Timer 100ms
    global actualTick, actualTick, actualTime, StartTick, timer_pause, pause, fin, timer_fin, penalitee, temps_final, run, Query_ID
    if pause == 1:
        timer_pause += 1
        if timer_pause > 20:
            timer_pause = 0
            pause = 0
            uart_chrono.write("clrr".encode('utf-8'))#envoie couleur Red
            if interrupt_Sect1 == 1:
                GPIO.output(signal_souffleuse, 0)

    if pause == 0 and fin == 0:
        temps_final = actualTime
        uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))

    if fin == 1:
        timer_fin += 1
        if 30 < timer_fin < penalitee/100 + 30:
            temps_final += 1
            uart_chrono.write(temps_final)
        if timer_fin > 100:
            run = 0  # course terminée
            timer_fin = 0
            fin = 0
            Query_ID = None
            GPIO.output(start_barrier, 1)
            timer_chrono.stop()
            uart_chrono.write("rien".encode('utf-8'))
            print('fin')


#					calcul de l'heure de fin de course
def final_hour(a):
    global ms_start, time_finish_ms, ms_finish, s_finish, h_finish, m_finish
    time_finish_ms = a + ms_start
    ms_finish = time_finish_ms % 1000
    s_finish = ((time_finish_ms // 1000) % 60)
    m_finish = (time_finish_ms // (1000 * 60)) % 60
    h_finish = (time_finish_ms // (1000 * 60 * 60)) % 24


#					calcul de l'heure de fin du secteur 1
def secteur1_hour(a):
    global ms_sect1, time_sect1_ms, s_sect1, m_sect1, h_sect1, ms_start
    time_sect1_ms = a + ms_start
    ms_sect1 = time_sect1_ms % 1000
    s_sect1 = ((time_sect1_ms // 1000) % 60)
    m_sect1 = (time_sect1_ms // (1000 * 60)) % 60
    h_sect1 = (time_sect1_ms // (1000 * 60 * 60)) % 24

#					calcul de l'heure de fin du secteur 2
def secteur2_hour(a):
    global ms_sect2, time_sect2_ms, s_sect2, m_sect2, h_sect2, ms_start
    time_sect2_ms = a + ms_start
    ms_sect2 = time_sect2_ms % 1000
    s_sect2 = ((time_sect2_ms // 1000) % 60)
    m_sect2 = (time_sect2_ms // (1000 * 60)) % 60
    h_sect2 = (time_sect2_ms // (1000 * 60 * 60)) % 24


#					Fonction enregistrement
def start_record():
    res = requests.get(obs_api + "start")
    print(res)


def plan2_record():
    res = requests.get(obs_api + "sector/2")
    print(res)


def plan3_record():
    res = requests.get(obs_api + "sector/3")
    print(res)


def stop_record():
    res = requests.get(obs_api + "finish")
    print(res)


def upload(id):
    res = requests.get(obs_api + "upload/" + str(id))
    print(res)


def get_id_car(Query_ID):
    res = requests.get(jelastic_api + "car/query-id/" + Query_ID)
    print(res)
    return res.json()["id_car"]


def get_bonus(id_car):
    print('test_bonus')
    res = requests.get(jelastic_api + "activity/by-car/" + str(id_car))
    print(res, 'test_bonus2')
    json = res.json()
    bonus = []
    for test in json:
        if test['id_section'] not in bonus:
            bonus.append(test['id_section'])

    return bonus


def bonus_activation(bonus):
    global penalitee
    if 1 not in bonus:
        #activation bonus informaticiens
        penalitee += 2
        print('bonus1')
    if 2 in bonus:
         #activation bonus automaticiens
         GPIO.output(bonus_aut_out, 1)
         print('bonus2')
    if 4 in bonus:
         #activation bonus électroniciens
         GPIO.output(bonus_elt_out, 1)
         print('bonus4')
    if 5 in bonus:
         #activation bonus micromécaniciens
         GPIO.output(bonus_mmc_out, 1)
         print('bonus5')
    if 6 not in bonus:
        #activation bonus laborantins
        penalitee += 2
        print('bonus6')
    if 7 in bonus:
         #activation bonus dessinateurs
         GPIO.output(bonus_dcm_out, 1)
         print('bonus7')

#					fonction interrupteur START
def Interrupt_Start(unused):
    global interrupt_Start, interrupt_Stop, interrupt_Sect1, interrupt_Sect2, StartTick, soft_timer, dixieme, StartTime, ms_start, run, timer_chrono
    if interrupt_Sect1 == 0 and fin == 0 and run == 0:
        interrupt_Stop = 0
        if interrupt_Start == 0:
            dixieme = 0
            run = 1
            StartTime = time.localtime()
            ms_start = ((StartTime.tm_hour * 3600000) + (StartTime.tm_min * 60000) + (StartTime.tm_sec * 1000))
            print(str(StartTime.tm_sec))
            Start_Hour = ("{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.000Z".format(str(StartTime.tm_year), str(StartTime.tm_mon),
                                                                                str(StartTime.tm_mday), str(StartTime.tm_hour),
                                                                                str(StartTime.tm_min), str(StartTime.tm_sec)))
            StartTick = time.perf_counter_ns()
            interrupt_Start = 1
            soft_timer = RepeatedTimer(0.01, runtime_handler)
            timer_chrono = RepeatedTimer(0.1, runtime_handler_chrono)
            dictionary["race_start"] = Start_Hour
            print(dictionary)
            print("\nStart: ", end='\t')
            print(Start_Hour)
            # start_record()
            GPIO.output(signal_run, 1)
            GPIO.output(start_barrier, 0)
            GPIO.output(capt1_barrier, 1)


#					fonction interrupteur SECTEUR 1
def Interrupt_Sect1(unused):
    global interrupt_Start, interrupt_Stop, interrupt_Sect2, interrupt_Sect1, capteur_vitesse_2, StopTick, TotalTime, StartTick, soft_timer, StopTime, timer_chrono, timer_pause, pause, StartTime
    if capteur_vitesse_2 == 1:
        capteur_vitesse_2 = 0
        if interrupt_Sect1 == 0:
            try:
                Sect1_Tick = time.perf_counter_ns()
                interrupt_Sect1 = 1
                Time_Sect1 = (Sect1_Tick - StartTick) // 1000000
                secteur1_hour(Time_Sect1)
                timer_pause = 0
                pause = 1
                uart_chrono.write("clrg".encode('utf-8'))#envoie couleur Green
                uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
                print(str(h_sect1),str(m_sect1), str(s_sect1),str(ms_sect1))
                Sect1_Hour = ("{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.{:0>3}Z".format(str(StartTime.tm_year),
                                                                                       str(StartTime.tm_mon),
                                                                                       str(StartTime.tm_mday),
                                                                                       str(int(h_sect1)),
                                                                                       str(int(m_sect1)), str(int(s_sect1)),
                                                                                       str(int(ms_sect1))))
                print("Sect1: ", end='\t')
                print(Sect1_Hour)
                dictionary["sector1"] = Sect1_Hour
                print(dictionary)
                GPIO.output(signal_souffleuse, 1)
                GPIO.output(sect1_barrier, 0)
                GPIO.output(sect2_barrier, 1)
                # plan2_record()
            except Exception as e:
                print('erreur', e)



#					fonction interrupteur SECTEUR 2
def Interrupt_Sect2(unused):
    global interrupt_Start, interrupt_Stop, interrupt_Sect2, interrupt_Sect1, StopTick, TotalTime, StartTick, soft_timer, StopTime, timer_chrono, timer_pause, pause
    if interrupt_Sect1 == 1:
        interrupt_Sect1 = 0
        if (interrupt_Sect2 == 0):
            Sect2_Tick = time.perf_counter_ns()
            interrupt_Sect2 = 1
            Time_Sect2 = (Sect2_Tick - StartTick) // 1000000
            secteur2_hour(Time_Sect2)
            timer_pause = 0
            pause = 1
            uart_chrono.write("clrg".encode('utf-8'))#envoie couleur Green
            uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
            Sect2_Hour = ("{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.{:0>3}Z".format(str(StartTime.tm_year), str(StartTime.tm_mon),
                                                                                   str(StartTime.tm_mday), str(int(h_sect2)),
                                                                                   str(int(m_sect2)), str(int(s_sect2)),
                                                                                   str(int(ms_sect2))))
            print("Sect2: ", end='\t')
            print(Sect2_Hour)
            dictionary["sector2"] = Sect2_Hour
            print(dictionary)
            GPIO.output(sect2_barrier, 0)
            GPIO.output(stop_barrier, 1)
            # plan3_record()


#					fonction interrupteur STOP
def Interrupt_Stop(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, StopTick, pause, TotalTime, StartTick, timer_chrono, soft_timer, StopTime, run, authentification, token_str, ms_finish, actualTime, fin
    if interrupt_Sect2 == 1:
        interrupt_Sect2 = 0
        if interrupt_Stop == 0:
            pause = 0
            fin = 1
            interrupt_Stop = 1
            StopTick = time.perf_counter_ns()
            TotalTime = (StopTick - StartTick) // 1000000
            print(StopTick)
            print(StartTick)
            print(TotalTime)
            soft_timer.stop()
            final_hour(TotalTime + penalitee)
            if ((ms_finish % 10) >= 5):
                actualTime += 1
            print(actualTime)
            uart_chrono.write("clrr".encode('utf-8'))#envoie couleur Red
            uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
            print("Stop: ", end='\t')
            Finish_Hour = (
                "{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.{:0>3}Z".format(str(StartTime.tm_year), str(StartTime.tm_mon),
                                                                         str(StartTime.tm_mday), str(int(h_finish)),
                                                                         str(int(m_finish)), str(int(s_finish)), str(int(ms_finish))))
            print(Finish_Hour)
            dictionary["race_finish"] = Finish_Hour
            dictionary["query_id"] = Query_ID
            print(dictionary)
            soft_timer.stop()
            GPIO.output(stop_barrier, 0)
            GPIO.output(signal_run, 0)
            GPIO.output(bonus_dcm_out, 0)
            GPIO.output(bonus_mmc_out, 0)
            GPIO.output(bonus_elt_out, 0)
            GPIO.output(bonus_aut_out, 0)

            # stop_record()
            r = requests.post(jelastic_api + "race/query-id/", headers={'Authorization': token_str}, json=dictionary)
            print(r.status_code)
            print(token_str)
            if (r.status_code == 401):
                res = requests.post(jelastic_api + "authentication/section/", json=authentification)
                authentification["token"] = res.json()['token']
                token_str = "Bearer " + str(authentification["token"])
                r = requests.post(jelastic_api + "race/query-id/", headers={'Authorization': token_str},
                                   json=dictionary)
            print(r.json())
            # threading.Thread(target=upload, args=(r.json()["id_race"],))


def Capteur_Vitesse_1(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, capteur_vitesse_1, actualTime, time_capt_vit_1
    if interrupt_Start == 1:
        interrupt_Start = 0
        print(capteur_vitesse_1)
        if capteur_vitesse_1 == 0:
            time_capt_vit_1 = time.perf_counter_ns()
            capteur_vitesse_1 = 1
            GPIO.output(start_barrier, 0)
            GPIO.output(capt1_barrier, 1)


def Capteur_Vitesse_2(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, capteur_vitesse_1, capteur_vitesse_2, actualTime, time_capt_vit_1
    if capteur_vitesse_1 == 1:
        capteur_vitesse_1 = 0
        if capteur_vitesse_2 == 0:
            DiffTemps = (time.perf_counter_ns() - time_capt_vit_1)/1000000
            print(DiffTemps)
            vitesse = (distance/DiffTemps) * 3.6
            capteur_vitesse_2 = 1
            dictionary["speed"] = vitesse
            print(vitesse)
            GPIO.output(capt2_barrier, 0)
            GPIO.output(sect1_barrier, 1)


            #					Boucle

GPIO.add_event_detect(S1, GPIO.RISING, callback=Interrupt_Start, bouncetime=200)
GPIO.add_event_detect(S2, GPIO.RISING, callback=Interrupt_Stop)
GPIO.add_event_detect(S3, GPIO.RISING, callback=Interrupt_Sect1)
GPIO.add_event_detect(S4, GPIO.RISING, callback=Interrupt_Sect2)
GPIO.add_event_detect(S5, GPIO.RISING, callback=Capteur_Vitesse_1)
GPIO.add_event_detect(S6, GPIO.RISING, callback=Capteur_Vitesse_2)

test = QRReader()
while True:
    pass
    if run == 0 and Query_ID is None:#si aucune course n'est en cours lire le qr
        if not test.is_running():
            test.start_detection()

        if test.qr != old_qr and test.qr is not None:
            old_qr = test.qr
            Query_ID = test.qr
            test.stop_detection()
            bonus_activation(get_bonus(1))
            #start_record()
            print (Query_ID)


