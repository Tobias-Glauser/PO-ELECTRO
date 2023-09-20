import time
import serial
import RPi.GPIO as GPIO
# from machine import Timer, Pin, UART, I2C
import requests
import pcf8575
import threading
import atexit
from timerV2 import RepeatedTimer
from serial.tools import list_ports
# from machine import Timer

# while True:
#     print(time.perf_counter())
#     time.sleep(1)


jelastic_api = 'https://voiture.divtec.me/api/'
obs_api = 'http://192.168.1.100/obs/'

#					Initialisation UART pour le chrono
# for port in list_ports.comports():
#     print(port)
uart_chrono = serial.Serial('/dev/ttyAMA0', 9600, parity=serial.PARITY_NONE,
  stopbits=serial.STOPBITS_ONE,
  bytesize=serial.EIGHTBITS,
  timeout=1)


#					Initialisation UART pour le scanner QR
# uart = UART(0, baudrate=57600, tx=Pin(0), rx=Pin(1))
# uart.init(bits=8, parity=None, stop=1)


#					Initialisation I2C pour le pcf8575
# i2c = I2C(1, scl=Pin(2), sda=Pin(3))
# pcf = pcf8575.PCF8575(i2c, 0x20)

#

					# Données à transférer
dictionary = {
    "query_id": None,
    "race_finish": None,
    "sector1": None,
    "secotr2": None,
    "race_start": None,
    "speed": 65.5
}

authentification = {
    "section": "race",
    "password": "Ch10r3.0d1n3tt3?G1@Ut0b_1nF$G@3tM1c!G1g@Ju1_313c",
    "token": None
}

#					Variables
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
soft_timer = None
GPIO.setmode(GPIO.BCM)
S1 = 26#start
S2 = 0#stop
S3 = 6#sect1
S4 = 5#sect2
S5 = 19#catp1
S6 = 13#capt2
state_pin = 21
GPIO.setup(S1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S4, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S5, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(S6, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(state_pin, GPIO.OUT)
# state_pin = machine.Pin(14, machine.Pin.OUT)
Query_ID = '4357'
penalitee = 0
DiffTemps = 0
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
    global actualTick, actualTick, actualTime, StartTick, timer_pause, pause, fin, timer_fin
    timer_pause += 1

    if timer_pause > 30:
        timer_pause = 0
        pause = 0
        GPIO.output(state_pin, 0)

    if (pause == 0 and fin == 0):
        uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
        # print("actualTime")

    if fin == 1:
        timer_fin += 1
        if timer_fin > 100:
            timer_fin = 0
            fin = 0
            timer_chrono.stop()
            uart_chrono.write("rien".encode('utf-8'))
            print('fin')


#					calcul de l'heure de fin de course
def final_hour(a):
    global ms_start, time_finish_ms, ms_finish, s_finish, h_finish, m_finish
    time_finish_ms = a + ms_start
    ms_finish = (time_finish_ms) % 1000
    s_finish = ((time_finish_ms // 1000) % 60)
    m_finish = (time_finish_ms // (1000 * 60)) % 60
    h_finish = (time_finish_ms // (1000 * 60 * 60)) % 24


#					calcul de l'heure de fin du secteur 1
def secteur1_hour(a):
    global ms_sect1, time_sect1_ms, s_sect1, m_sect1, h_sect1, ms_start
    time_sect1_ms = a + ms_start
    ms_sect1 = (time_sect1_ms) % 1000
    s_sect1 = ((time_sect1_ms // 1000) % 60)
    m_sect1 = (time_sect1_ms // (1000 * 60)) % 60
    h_sect1 = (time_sect1_ms // (1000 * 60 * 60)) % 24


#					calcul de l'heure de fin du secteur 2
def secteur2_hour(a):
    global ms_sect2, time_sect2_ms, s_sect2, m_sect2, h_sect2, ms_start
    time_sect2_ms = a + ms_start
    ms_sect2 = (time_sect2_ms) % 1000
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


# def bonus_activation(bonus):
#     if 1 in bonus:
#         penalitee += 2 #activation bonus informaticiens
#     if 2 in bonus:
#          pcf.pin(14, 1)#activation bonus automaticiens
#     if 4 in bonus:
#          pcf.pin(12, 1)#activation bonus électroniciens
#     if 5 in bonus:
#          pcf.pin(15, 1)#activation bonus micromécaniciens
#     if 6 in bonus:
#         penalitee += 2 #activation bonus laborantins
#     if 7 in bonus:
#          pcf.pin(13, 1)#activation bonus dessinateurs

#					fonction interrupteur START
def Interrupt_Start(unused):
    print(1)
    global interrupt_Start, interrupt_Stop, interrupt_Sect1, interrupt_Sect2, StartTick, soft_timer, dixieme, StartTime, ms_start, run, timer_chrono
    if interrupt_Sect1 == 0 and fin == 0 and run == 0:
        interrupt_Stop = 0
        if interrupt_Start == 0:
            dixieme = 0
            pause = 0
            minute = 0
            run = 1
            StartTime = time.localtime()
            ms_start = ((StartTime.tm_hour * 3600000) + (StartTime.tm_min * 60000) + (StartTime.tm_sec * 1000))
            print(str(StartTime.tm_sec))
            Start_Hour = ("{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.000Z".format(str(StartTime.tm_year), str(StartTime.tm_mon),
                                                                                str(StartTime.tm_mday), str(StartTime.tm_hour),
                                                                                str(StartTime.tm_min), str(StartTime.tm_sec)))
            StartTick = time.perf_counter_ns()
            interrupt_Start = 1
            # soft_timer = Timer(mode=Timer.PERIODIC, period=10, callback=runtime_handler)
            # timer_chrono = Timer(mode=Timer.PERIODIC, period=100, callback=runtime_handler_chrono)
            soft_timer = RepeatedTimer(0.01, runtime_handler)
            timer_chrono = RepeatedTimer(0.1, runtime_handler_chrono)
            dictionary["race_start"] = Start_Hour
            print(dictionary)
            print("\nStart: ", end='\t')
            print(Start_Hour)
            #             pcf.pin(16, 1)
            start_record()
            get_bonus(1)


#					fonction interrupteur SECTEUR 1
def Interrupt_Sect1(unused):
    global interrupt_Start, interrupt_Stop, interrupt_Sect2, interrupt_Sect1, capteur_vitesse_2, StopTick, TotalTime, StartTick, soft_timer, StopTime, timer_chrono, timer_pause, pause, StartTime
    if capteur_vitesse_2 == 1:
        capteur_vitesse_2 = 0
        if interrupt_Sect1 == 0:
            try:
                Sect1_Tick = time.perf_counter()
                interrupt_Sect1 = 1
                Time_Sect1 = (Sect1_Tick - StartTick) // 1000
                secteur1_hour(Time_Sect1)
                timer_pause = 0
                pause = 1
                GPIO.output(state_pin, 1)
                print("actualTime")
                uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
                print("actualTime")
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
                plan2_record()
            except Exception as e:
                print('erreur', e)



#					fonction interrupteur SECTEUR 2
def Interrupt_Sect2(unused):
    global interrupt_Start, interrupt_Stop, interrupt_Sect2, interrupt_Sect1, StopTick, TotalTime, StartTick, soft_timer, StopTime, timer_chrono, timer_pause, pause
    if interrupt_Sect1 == 1:
        interrupt_Sect1 = 0
        if (interrupt_Sect2 == 0):
            print('test4')
            Sect2_Tick = time.perf_counter()
            interrupt_Sect2 = 1
            Time_Sect2 = (Sect2_Tick - StartTick) // 1000
            secteur2_hour(Time_Sect2)
            timer_pause = 0
            pause = 1
            GPIO.output(state_pin, 1)
            uart_chrono.write("{:04d}".format(actualTime).encode('utf-8'))
            Sect2_Hour = ("{:4}-{:0>2}-{:0>2}T{:0>2}:{:0>2}:{:0>2}.{:0>3}Z".format(str(StartTime.tm_year), str(StartTime.tm_mon),
                                                                                   str(StartTime.tm_mday), str(int(h_sect2)),
                                                                                   str(int(m_sect2)), str(int(s_sect2)),
                                                                                   str(int(ms_sect2))))
            print("Sect2: ", end='\t')
            print(Sect2_Hour)
            dictionary["sector2"] = Sect2_Hour
            print(dictionary)
            plan3_record()


#					fonction interrupteur STOP
def Interrupt_Stop(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, StopTick, pause, TotalTime, StartTick, timer_chrono, soft_timer, StopTime, run, authentification, token_str, ms_finish, actualTime, fin
    if interrupt_Sect2 == 1:
        interrupt_Sect2 = 0
        if interrupt_Stop == 0:
            run = 0  # course terminée
            pause = 0
            fin = 1
            interrupt_Stop = 1
            StopTick = time.perf_counter()
            TotalTime = (StopTick - StartTick) // 1000
            soft_timer.stop()
            final_hour(TotalTime)
            if ((ms_finish % 10) >= 5):
                actualTime += 1
            print(actualTime)
            GPIO.output(state_pin, 0)
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
            #             pcf.port = 0x0000
            stop_record()
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
            threading.Thread(target=upload, args=(r.json()["id_race"],))


def Capteur_Vitesse_1(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, capteur_vitesse_1, actualTime, Temps1
    if interrupt_Start == 1:
        interrupt_Start = 0
        print(capteur_vitesse_1)
        if capteur_vitesse_1 == 0:
            Temps1 = actualTime
            capteur_vitesse_1 = 1


def Capteur_Vitesse_2(unused):
    global interrupt_Start, interrupt_Sect1, interrupt_Sect2, interrupt_Stop, capteur_vitesse_1, capteur_vitesse_2, actualTime, Temps1
    if capteur_vitesse_1 == 1:
        capteur_vitesse_1 = 0
        if capteur_vitesse_2 == 0:
            Temps2 = actualTime
            DiffTemps = Temps2 - Temps1
            vitesse = (distance/DiffTemps) * 360
            capteur_vitesse_2 = 1
            print(vitesse)


#					Boucle

GPIO.add_event_detect(S1, GPIO.RISING, callback=Interrupt_Start, bouncetime=200)
GPIO.add_event_detect(S2, GPIO.RISING, callback=Interrupt_Stop)
GPIO.add_event_detect(S3, GPIO.RISING, callback=Interrupt_Sect1)
GPIO.add_event_detect(S4, GPIO.RISING, callback=Interrupt_Sect2)
GPIO.add_event_detect(S5, GPIO.RISING, callback=Capteur_Vitesse_1)
GPIO.add_event_detect(S6, GPIO.RISING, callback=Capteur_Vitesse_2)
while True:
    pass

#     if (run == 0):
#         QR_data = uart.read()
#         if QR_data != None:
#             Query_ID = (QR_data[-4:])
#             record_start()
#
#             print (Query_ID)


