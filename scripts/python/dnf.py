import multiprocessing
import random
import sqlite3
import sys
import threading
import time
from pathlib import Path



import pygetwindow as gw
import torch
from PIL import ImageGrab
from ultralytics import YOLO

shot_pic = 0

pick = 0  # 0为不捡

parent_dir = Path(__file__).resolve().parent.parent
sys.path.append(str(parent_dir))
from lib_all import read_serial_and_forward
from lib_all import init
from lib_all import jbl_close
from lib_all import speedtest_xy
from lib_all import pickandmove
from lib_all import show_time
from lib_all import move_abit
from lib_all import out_map_lypb
from lib_all import cap_lock_open
from lib_all import cap_lock_close
from lib_all import find_breakpoint
from lib_all import use_SN_fand_inf
from lib_all import battles_over_sqlite
from lib_all import over_sell_repair
from lib_all import over_sell_repair_fj
from lib_all import mid_night_outwindow
from lib_all import fj
from lib_all import finish_every_mission
from lib_all import slect_char
from lib_lypb import char_name_skill


def process_check(yolo_queue, input_queue, o_received_event, xt, yt, windowx, windowy, width, height, row, qq):
    global results, model, class_ids, xyxy, xywh, conf,now_shot,char_x, char_y,char_x1, char_x2, char_y2
    # 初始化变量
    buff_ok, a, room3_door_y, active_num, room_num = 0, 0, 0, 0, 1
    check_ui, check_again, check_sproom, check_bossdoor, ban_pick = 0, 0, 0, 0, 0
    char_x, char_y,char_x1, char_x2, char_y2=0,0,0,0,0
    loop_t = 0
    now_shot=0
    class_ids, xyxy, xywh, conf = [], [], [], []
    # 初始化时间标记
    every_mission, start_time = time.time(), time.time()
    # 读取数据库数据
    SN, job_name, battles_number, last_battles_time, need_fj, start_tip, char_tail = row[0], row[2], row[4], row[5], \
        row[6], row[9], row[11]
    print(job_name, battles_number, last_battles_time, need_fj, start_tip)
    results = {}
    read_yolo_result_1 = True
    now_shot = 1
    # 读取图像识别结果
    def read_yolo_result():
        global results,class_ids,xyxy,xywh,conf,char_x, char_y,char_x1, char_x2, char_y2
        # 等待指令
        while read_yolo_result_1:
            if not yolo_queue.empty():
                # 从队列中读取数据并赋值
                data = yolo_queue.get()
                if data is not None:  # 假设使用None作为特殊信号
                    results = data
                    class_ids = results['class_ids']
                    xyxy = results['xyxy']
                    xywh = results['xywh']
                    conf = results['conf']
                    if 0 in class_ids:
                        num_index = class_ids.index(0)
                        char_x1, char_x2, char_y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                        char_x, char_y = char_x1 + (char_x2 - char_x1) / 2, char_y2 + char_tail
                elif data is None:
                    break

    # 等待动作完毕
    def wait_move_ready(o_received_event):
        while True:
            if o_received_event.is_set():
                # 现在我们知道子进程已经接收到了'o'，可以进行后续操作
                # print("动作完成")
                # 清除设置状态
                o_received_event.clear()
                break

    # 使用技能列表
    def use_skill_list(skill_list):
        for i in skill_list:
            input_queue.put(str(i))
            wait_move_ready(o_received_event)
            if i=='y':
                time.sleep(8)
            if job_name=='奶妈' and i=='t':
                time.sleep(4.5)
            else:
                time.sleep(1.1)

    # 运行子线程读取图像识别结果
    thread_result = threading.Thread(target=read_yolo_result)
    thread_result.start()

    time.sleep(3.5)

    # 链接数据库
    db_name = r'X:\predict\main\main_' + str(qq) + '.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # 获得技能释放列表
    frist_list, after_list, boss_list, often_list, sp_list = char_name_skill(job_name)

    while True:
        #临时截图
        #im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
        #im.save('X:/lypb/' + str(int(time.time())) + '.png')
        # -----------------计数和运行时间限制-----------------
        active_num = active_num + 1
        hours, minutes, seconds = show_time(inputtime=start_time)
        print('-------' + '当前循环次数：' + str(
            active_num) + '---总体耗费时间:' + f"{hours}小时{minutes}分钟{seconds}秒" + '-------')
        hours, minutes, seconds = show_time(inputtime=every_mission)
        print('单图耗费时间:' + f"{hours}小时{minutes}分钟{seconds}秒")
        # 三个小时超时暂停
        if time.time() - start_time > 6000:
            read_yolo_result_1 = False
            sys.exit()
        # 超过5分钟超时退出
        elif time.time() - every_mission > 300:
            print('超时退出')
            rr = out_map_lypb(o_received_event, input_queue, windowx, windowy, modelname, width, height)
            if rr == 1:
                every_mission = time.time()
                print('已经重新开始')
                room_num, buff_ok = 1, 0
                continue
            elif rr == 0:
                print('无法重新开始，进入结束流程')
                print('没疲劳了')
                # F12返回城镇
                input_queue.put('l')
                wait_move_ready(o_received_event)
                time.sleep(10)
                # 午夜过后1小时内，回城可能有弹窗
                mid_night_outwindow(o_received_event, input_queue, windowx, windowy)
                model = YOLO(modelname)
                # 进行分解
                if need_fj == 1:
                    # 选择人物，回赛丽亚房间
                    slect_char(SN, o_received_event, input_queue, windowx, windowy, model, width, height, chenghao_number)
                    # 卖、修理
                    over_sell_repair(o_received_event, input_queue, windowx, windowy, SN)
                    # 分解
                    fj(o_received_event, input_queue, windowx, windowy)
                elif need_fj == 0:
                    # 选择人物，回赛丽亚房间
                    slect_char(SN, o_received_event, input_queue, windowx, windowy, model, width, height, chenghao_number)
                    # 开始卖
                    over_sell_repair_fj(o_received_event, input_queue, windowx, windowy, SN)
                # 每日任务
                finish_every_mission(o_received_event, input_queue, windowx, windowy)
                # 关闭资源
                print('关闭判定子进程资源')
                read_yolo_result_1 = False
                cursor.close()
                conn.close()
                break
        else:
            if random.randrange(1, 120) == 50:
                window_title = '地下城与勇士：创新世纪'  # 替换成你想要截取的窗口的标题
                window = gw.getWindowsWithTitle(window_title)[0]
                window.activate()
                print('随机激活窗口')

        # -----------------信息初处理-----------------
        print('所有的类id：' + str(class_ids))

        # -----------------隐藏UI-----------------
        if 4 in class_ids:
            print('发现ui')
            input_queue.put('j')
            wait_move_ready(o_received_event)
            time.sleep(2.5)
            continue
        # ----------------再次挑战/停止----------------
        if 12 in class_ids and 20 in class_ids :
            # -----------------发现再次挑战-----------------
            num_index = class_ids.index(12)
            print(conf[num_index])
            if conf[num_index] > 0.8:
                time.sleep(5)
                print('发现再次挑战')
                print('boss死了')
                # 捡东西
                input_queue.put('9')
                wait_move_ready(o_received_event)
                #随机修理
                if random.randrange(1, 3)==2:
                    input_queue.put('3')
                    wait_move_ready(o_received_event)
                # 去掉加百列
                jbl_close(o_received_event, input_queue, windowx, windowy)
                # 写入数据
                battles_over_sqlite(qq, cursor, conn, SN)
                for i in range(0, 60):
                    if 13 in class_ids:
                        print('已经重新开始')
                        room_num, buff_ok = 1, 0
                        every_mission = time.time()
                        break
                    elif i%10==0:
                        #激活窗口
                        window_title = '地下城与勇士：创新世纪'  # 替换成你想要截取的窗口的标题
                        window = gw.getWindowsWithTitle(window_title)[0]
                        window.activate()
                        print('随机激活窗口')
                        #捡东西
                        input_queue.put('9')
                        wait_move_ready(o_received_event)
                        #再次挑战
                        input_queue.put('v')
                        wait_move_ready(o_received_event)
                        time.sleep(0.5)
                    else:
                        print('未检测到一号房间')
                        time.sleep(0.5)
                if buff_ok == 0:
                    time.sleep(2)
                    continue
                else:
                    print('没疲劳了')
                    # F12返回城镇
                    input_queue.put('l')
                    wait_move_ready(o_received_event)
                    time.sleep(10)
                    # 午夜过后1小时内，回城可能有弹窗
                    mid_night_outwindow(o_received_event, input_queue, windowx, windowy)
                    model = YOLO(modelname)
                    # 进行分解
                    if need_fj == 1:
                        # 选择人物，回赛丽亚房间
                        slect_char(SN, o_received_event, input_queue, windowx, windowy, model, width, height, chenghao_number)
                        # 卖、修理
                        over_sell_repair(o_received_event, input_queue, windowx, windowy, SN)
                        # 分解
                        fj(o_received_event, input_queue, windowx, windowy)
                    elif need_fj == 0:
                        # 选择人物，回赛丽亚房间
                        slect_char(SN, o_received_event, input_queue, windowx, windowy, model, width, height, chenghao_number)
                        # 开始卖
                        over_sell_repair_fj(o_received_event, input_queue, windowx, windowy, SN)
                    # 每日任务
                    finish_every_mission(o_received_event, input_queue, windowx, windowy)
                    # 关闭资源
                    read_yolo_result_1 = False
                    cursor.close()
                    conn.close()
                    break

        # ---------------确定人物坐标---------------
        if 0 in class_ids:
            print('推测人物中下角坐标：' + str(int(char_x1 + (char_x2 - char_x1) / 2)) + ',' + str(char_y2 + char_tail))
        else:
            if room_num == 8:
                continue
            time.sleep(0.5)
            move_abit(fx=6, jl=80, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
            continue

        # -----------------维持sp技能-----------------
        if sp_list != [] and int(time.time()) - loop_t > 45:
            input_queue.put(sp_list[0])
            wait_move_ready(o_received_event)
            loop_t = int(time.time())

        # ----------------房间判断-----------------
        if (13 in class_ids or 14 in class_ids or
                15 in class_ids or 16 in class_ids or
                17 in class_ids or 18 in class_ids or
                19 in class_ids or 20 in class_ids):
            # ----------------1号房间-----------------
            if 13 in class_ids:
                check_sproom = 0
                check_ui = 1
                ban_pick = 0
                if room_num == 1:
                    print('当前处于第' + str(room_num) + '个房间')
                    # 如果buff状态没有上
                    if buff_ok == 0:
                        use_skill_list(skill_list=frist_list)
                        loop_t = int(time.time())
                        buff_ok = buff_ok + 1
                        continue
                elif room_num == 2:
                    thing_x = char_x + 180
                    thing_y = char_y - 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 1
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    room_num = 1
                    print('当前处于第' + str(room_num) + '个房间')
            # ----------------2号房间-----------------
            elif 14 in class_ids:
                check_ui = 0
                check_sproom = 0
                check_again = 0
                ban_pick = 0
                if room_num == 1:
                    # if after_list == [] or after_list[0] == '':
                    #     pass
                    # else:
                    #     input_queue.put(after_list[0])
                    #     wait_move_ready(o_received_event)
                    room_num = 2
                    print('第一次进入第' + str(room_num) + '个房间')
                elif room_num == 2:
                    room_num = 2
                    print('当前处于第' + str(room_num) + '个房间')

                elif room_num == 3:
                    thing_x = char_x - 180
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 2
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 2
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------3号房间-----------------
            elif 15 in class_ids:
                check_sproom = 0
                check_ui = 1
                check_again = 0
                if room_num == 2:
                    # if after_list == [] or after_list[1] == '':
                    #     pass
                    # else:
                    #     input_queue.put(after_list[1])
                    #     wait_move_ready(o_received_event)
                    room_num = 3
                    print('第一次进入第' + str(room_num) + '个房间')
                    if class_ids.count(3) == 0 and 8 not in class_ids:
                        move_abit(fx=6, jl=100, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
                        continue
                elif room_num == 3:
                    room_num = 3
                    print('当前处于第' + str(room_num) + '个房间')
                elif room_num == 4:
                    thing_x = char_x - 180
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 3
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 50
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 3
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------4号房间-----------------
            elif 16 in class_ids:
                check_sproom = 0
                check_ui = 0
                if room_num == 3:
                    # if after_list == [] or after_list[2] == '':
                    #     pass
                    # else:
                    #     input_queue.put(after_list[2])
                    #     wait_move_ready(o_received_event)
                    room_num = 4
                    print('第一次进入第' + str(room_num) + '个房间')
                elif room_num == 4:
                    print('当前处于第' + str(room_num) + '个房间')

                elif room_num == 5:
                    thing_x = char_x - 180
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 4
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 4
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------5号房间-----------------
            elif 17 in class_ids:
                check_sproom = 1
                check_ui = 1
                check_again = 0
                check_bossdoor = 0
                if room_num == 4:
                    room_num = 5
                    print('第一次进入第' + str(room_num) + '个房间')
                    # if after_list == [] or after_list[3] == '':
                    #     pass
                    # else:
                    #     input_queue.put(after_list[3])
                    #     wait_move_ready(o_received_event)
                elif room_num == 5:
                    print('当前处于第' + str(room_num) + '个房间')
                    if class_ids.count(1) == 0:
                        move_abit(fx=8, jl=80,xt=xt,yt=yt,input_queue=input_queue,o_received_event=o_received_event)
                elif room_num == 6:

                    room_num = 5
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 5
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------6号房间-----------------
            elif 18 in class_ids:
                check_sproom = 1
                check_ui = 0
                check_again = 0
                check_bossdoor = 0
                if room_num == 5:
                    room_num = 6
                    print('第一次进入第' + str(room_num) + '个房间')
                    move_abit(fx=8,jl=40,xt=xt,yt=yt,input_queue=input_queue,o_received_event=o_received_event)
                    if after_list == [] or after_list[4] == '':
                        pass
                    elif 1 in class_ids:
                        pass
                    else:
                        input_queue.put(after_list[4])
                        wait_move_ready(o_received_event)
                        time.sleep(4)
                        if after_list == [] or after_list[5] == '':
                            pass
                        elif 1 in class_ids:
                            pass
                        else:
                            input_queue.put(after_list[5])
                            wait_move_ready(o_received_event)
                            time.sleep(4)
                            if after_list == [] or after_list[6] == '':
                                pass
                            elif 1 in class_ids:
                                pass
                            else:
                                input_queue.put(after_list[6])
                                wait_move_ready(o_received_event)
                                time.sleep(4)
                                if after_list == [] or after_list[7] == '':
                                    pass
                                elif 1 in class_ids:
                                    pass
                                else:
                                    input_queue.put(after_list[7])
                                    wait_move_ready(o_received_event)
                elif room_num == 6:
                    print('当前处于第' + str(room_num) + '个房间')

                elif room_num == 7:
                    thing_x = char_x - 180
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 5
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 6
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------7号房间-----------------
            elif 19 in class_ids:
                check_sproom = 1
                check_ui = 0
                check_again = 1
                check_bossdoor = 1
                if room_num == 6:
                    # if after_list == [] or after_list[8] == '':
                    #     pass
                    # else:
                    #     input_queue.put(after_list[8])
                    #     wait_move_ready(o_received_event)

                    room_num = 7
                    print('第一次进入第' + str(room_num) + '个房间')
                elif room_num == 7:
                    print('当前处于第' + str(room_num) + '个房间')
                else:
                    thing_x = char_x - 80
                    thing_y = char_y + 80
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    room_num = 6
                    print('当前处于第' + str(room_num) + '个房间')
                    continue
            # ----------------BOSS房间-----------------
            elif 20 in class_ids:
                check_sproom = 1
                check_ui = 1
                check_again = 1
                ban_pick = 1
                if room_num == 7:
                    room_num = 8
                    print('第一次进入BOSS当前处于第' + str(room_num) + '个房间')
                    move_abit(fx=6, jl=200, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
                    if boss_list == [] or boss_list[0] == '':
                        pass
                    else:
                        use_skill_list(skill_list=boss_list)

                room_num = 8
                print('BOSS当前处于第' + str(room_num) + '个房间')

            # ----------------其他房间-----------------
            else:
                check_sproom == 1
                if 8 in class_ids:
                    num_index = class_ids.index(8)
                    x1, x2, y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                    thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                    print('发现怪物' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    if often_list == [] or often_list[0] == '':
                        pass
                    else:
                        use_skill_list(skill_list=often_list)
                    continue
                if 3 in class_ids:
                    thing_x = char_x + 80
                    thing_y = char_y - 20
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)

                    if class_ids.count(3) >= 1:
                        index = [i for i, x in enumerate(class_ids) if x == 3]
                        thing_x, thing_y = xyxy[index[0]][2], xyxy[index[0]][3]
                        pickandmove(char_x=char_x, char_y=char_y,
                                    thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event
                                    )
                    continue
                else:
                    move_abit(fx=6, jl=150, xt=xt, yt=yt, input_queue=input_queue,
                              o_received_event=o_received_event)
                    continue

        # ----------------掉落物-金币-----------------
        if 8 in class_ids and ban_pick == 0:
            pick_over = 0
            if class_ids.count(8) == 1:  # 如果只有一个掉落物
                try:
                    num_index = class_ids.index(8)
                    if conf[num_index] > 0.8:
                        x1, x2, y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                        thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                        print('发现金币' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event, )
                        if shot_pic == 1:
                            im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
                            im.save('X:/lypb/' + str(int(time.time())) + '.png')
                        if pick == 1:
                            input_queue.put('x')
                            wait_move_ready(o_received_event)
                        time.sleep(0.5)
                        continue
                except ValueError or IndexError:
                    continue
            else:  # 如果多个掉落物
                pick_index_list = [i for i, x in enumerate(class_ids) if x == 8]
                for i in pick_index_list:
                    try:
                        if conf[i] > 0.8:
                            x1, x2, y2 = xyxy[i][0], xyxy[i][2], xyxy[i][3]
                            thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                            print('发现金币' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event, )
                            if shot_pic == 1:
                                im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
                                im.save('X:/lypb/' + str(int(time.time())) + '.png')
                            if pick == 1:
                                input_queue.put('x')
                                wait_move_ready(o_received_event)
                            pick_over = 1
                            break
                    except ValueError or IndexError:
                        continue
                if pick_over == 1:
                    continue

        # ----------------掉落物-装备-----------------
        if 10 in class_ids and ban_pick == 0:
            pick_over = 0
            if class_ids.count(10) == 1:  # 如果只有一个掉落物
                try:
                    num_index = class_ids.index(10)
                    if conf[num_index] > 0.7:
                        x1, x2, y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                        thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                        print('发现金币' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event, )
                        if shot_pic == 1:
                            im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
                            im.save('X:/lypb/' + str(int(time.time())) + '.png')
                        if pick == 1:
                            input_queue.put('x')
                            wait_move_ready(o_received_event)
                        continue
                except ValueError or IndexError:
                    continue
            else:  # 如果多个掉落物
                pick_index_list = [i for i, x in enumerate(class_ids) if x == 10]
                for i in pick_index_list:
                    try:
                        if conf[i] > 0.7:
                            x1, x2, y2 = xyxy[i][0], xyxy[i][2], xyxy[i][3]
                            thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                            print('发现金币' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt,
                                        yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event, )
                            if shot_pic == 1:
                                im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
                                im.save('X:/lypb/' + str(int(time.time())) + '.png')
                            if pick == 1:
                                input_queue.put('x')
                                wait_move_ready(o_received_event)
                            pick_over = 1
                            break
                    except ValueError or IndexError:
                        break
                if pick_over == 1:
                    continue

        # ----------------怪物定位-----------------
        elif 6 in class_ids and 1 not in class_ids:
            try:
                num_index = class_ids.index(6)
                x1, x2, y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                print('发现怪物' + '右下角坐标：' + str(thing_x) + ',' + str(thing_y))
                pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                            input_queue=input_queue, o_received_event=o_received_event)
                if often_list == [] or often_list[0] == '':
                    pass
                else:
                    use_skill_list(skill_list=often_list)
                time.sleep(0.5)
                continue
            except ValueError or IndexError:
                continue

        # ----------------怪物定位-----------------
        elif 7 in class_ids and room_num == 8:
            try:
                num_index = class_ids.index(7)
                x1, x2, y2 = xyxy[num_index][0], xyxy[num_index][2], xyxy[num_index][3]
                thing_x, thing_y = int(x1 + (x2 - x1) / 2), int(y2)
                print('发现boss' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                            input_queue=input_queue, o_received_event=o_received_event)
                if often_list == [] or often_list[0] == '':
                    pass
                else:
                    use_skill_list(skill_list=often_list)
                continue
            except ValueError or IndexError:
                continue

        # ----------------门定位-----------------
        elif 3 in class_ids :
            try:
                num_index = class_ids.index(3)
                thing_x, thing_y = xywh[num_index][0], xywh[num_index][1]
                print('发现开启的boss门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                            input_queue=input_queue, o_received_event=o_received_event)
                continue
            except ValueError or IndexError:
                continue

        # ----------------门定位-----------------
        elif 1 in class_ids and 4 not in class_ids:
            found_door_walk = 0
            num_index = class_ids.index(1)
            thing_x, thing_y = xywh[num_index][0], xywh[num_index][1]
            print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
            # ----------------一号房间发现门-----------------
            if room_num == 1:  # 只能一个门
                if abs(char_x - thing_x) < 50 and abs(char_y-thing_y)<30:
                    time.sleep(3.5)
                    move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                              o_received_event=o_received_event)
                    move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                              o_received_event=o_received_event)
                    continue
                else:
                    print('进入下一房间')
                    pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                input_queue=input_queue, o_received_event=o_received_event)
                    time.sleep(1)
                    continue
            # ----------------二号房间发现门-----------------
            elif room_num == 2:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    if 825 < thing_x < 960:  # 找到正确的门
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            time.sleep(3.5)
                            move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            found_door_walk = 1

                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                        continue
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                if 825 < thing_x < 960:  # 找到正确的门
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        time.sleep(3.5)
                                        move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                                    input_queue=input_queue, o_received_event=o_received_event)
                                        time.sleep(1)
                                        found_door_walk = 1
                                        need_c = 1
                                        break
                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    # 走完继续
                    if need_c == 1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                        continue
            # ----------------三号房间发现门-----------------
            elif room_num == 3:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    if 825 < thing_x < 960:  # 找到正确的门
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            time.sleep(3.5)
                            move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            continue
                    else:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 30
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                        continue
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                if 825 < thing_x < 960:  # 找到正确的门
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        time.sleep(3.5)
                                        move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                                    input_queue=input_queue, o_received_event=o_received_event)
                                        time.sleep(1)
                                        found_door_walk = 1
                                        need_c = 1
                                        break
                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    # 走完继续
                    if need_c == 1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                        continue
            # ----------------四号房间发现门-----------------
            elif room_num == 4:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    if 825 < thing_x < 960:  # 找到正确的门
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            time.sleep(3.5)
                            move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            continue
                    else:  # 如果没有符合要求的，往右上走
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                if 825 < thing_x < 960:  # 找到正确的门
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        time.sleep(3.5)
                                        move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                            input_queue=input_queue, o_received_event=o_received_event)
                                        found_door_walk = 1
                                        need_c = 1
                                        time.sleep(1)
                                        break
                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    # 走完继续
                    if need_c == 1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                        continue
            # ----------------五号房间发现门-----------------
            elif room_num == 5:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    # 找到正确的门
                    if 280 < thing_y < 435 and 510 < thing_x < 750:
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            time.sleep(3.5)
                            move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            continue
                    # 找到正确的门
                    elif 825 < thing_x < 960:
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            time.sleep(3.5)
                            move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            found_door_walk = 1
                            time.sleep(1)
                            continue
                    else:  # 如果没有符合要求的，往右上走
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                # 找到正确的门
                                if 310 < thing_y < 430 and 590 < thing_x < 675:
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        time.sleep(3.5)
                                        move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                            input_queue=input_queue, o_received_event=o_received_event)
                                        time.sleep(1)
                                        found_door_walk = 1
                                        need_c = 1
                                        break
                                # 找到正确的门
                                elif 825 < thing_x < 960:
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        time.sleep(3.5)
                                        move_abit(fx=4, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        move_abit(fx=6, jl=90, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                                    input_queue=input_queue, o_received_event=o_received_event)
                                        found_door_walk = 1
                                        time.sleep(1)
                                        need_c = 1
                                        break

                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    # 走完继续
                    if need_c == 1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
            # ----------------六号房间发现门-----------------
            elif room_num == 6:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    # 找到正确的门
                    if 825 < thing_x < 960:
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            move_abit(fx=4, jl=80, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            continue
                    else:  # 如果没有符合要求的，往右上走
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                # 找到正确的门
                                if 825 < thing_x < 960:
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        move_abit(fx=4, jl=80, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                                    input_queue=input_queue, o_received_event=o_received_event)
                                        time.sleep(1)
                                        found_door_walk = 1
                                        need_c = 1
                                        break
                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    # 走完继续
                    if need_c == 1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
            # ----------------七号房间发现门-----------------
            elif room_num == 7:
                if class_ids.count(1) == 1:  # 如果只发现一个门
                    # 找到正确的门
                    if 825 < thing_x < 960:
                        if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                            move_abit(fx=4, jl=80, xt=xt, yt=yt, input_queue=input_queue,
                                      o_received_event=o_received_event)
                            continue
                        else:
                            print('进入下一房间')
                            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                        input_queue=input_queue, o_received_event=o_received_event)
                            time.sleep(1)
                            continue
                    else:  # 如果没有符合要求的，往右上走
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
                else:  # 如果发现多个门
                    a = -1
                    found_door_walk = 1
                    need_c = 0
                    for i in class_ids:
                        a = a + 1
                        if i == 1:
                            try:
                                thing_x, thing_y = xywh[a][0], xywh[a][1]
                                print('发现开启的门' + '中心坐标：' + str(thing_x) + ',' + str(thing_y))
                                # 找到正确的门
                                if 825 < thing_x < 960:
                                    if abs(char_x - thing_x) < 50 and abs(char_y - thing_y) < 30:
                                        move_abit(fx=4, jl=80, xt=xt, yt=yt, input_queue=input_queue,
                                                  o_received_event=o_received_event)
                                        break
                                    else:
                                        print('进入下一房间')
                                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                                    input_queue=input_queue, o_received_event=o_received_event)
                                        time.sleep(1)
                                        found_door_walk = 0
                                        need_c=1
                                        break
                                else:
                                    continue
                            except ValueError or IndexError:
                                break
                    #走完继续
                    if need_c==1:
                        continue
                    # 如果没有符合要求的，往右上走
                    if found_door_walk != 1:
                        print('没有符合要求的门')
                        thing_x = char_x + 480
                        thing_y = char_y - 20
                        pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                                    input_queue=input_queue, o_received_event=o_received_event)
                        found_door_walk = 0
                        time.sleep(0.3)
        # ----------------行走操作一号房间-----------------
        if room_num == 1:
            print('所有判定已过，前进')
            thing_x = char_x + 280
            thing_y = char_y - 20
            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                        input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------二号房间-----------------
        elif room_num == 2:
            print('所有判定已过，前进')
            move_abit(fx=6, jl=280, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------三号房间-----------------
        elif room_num == 3:
            print('所有判定已过，前进')
            move_abit(fx=6, jl=280, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------四号房间-----------------
        elif room_num == 4:
            print('所有判定已过，前进')
            move_abit(fx=6, jl=280, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------五号房间-----------------
        elif room_num == 5:
            print('所有判定已过，前进')
            thing_x = char_x + 280
            thing_y = char_y - 50
            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                        input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------六号房间-----------------
        elif room_num == 6:
            print('所有判定已过，前进')
            thing_x = char_x + 30
            thing_y = char_y - 40
            pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                        input_queue=input_queue, o_received_event=o_received_event)
            time.sleep(0.3)
        # ----------------七号房间-----------------
        elif room_num == 7:

            if char_x > 900:
                print('到门边了,上下移动')
                move_abit(fx='8', jl=200, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
                move_abit(fx='2', jl=200, xt=xt, yt=yt, input_queue=input_queue, o_received_event=o_received_event)
                time.sleep(0.3)
            else:
                print('所有判定已过，前进')
                thing_x = char_x + 200
                thing_y = char_y - 50
                pickandmove(char_x=char_x, char_y=char_y, thing_x=thing_x, thing_y=thing_y, xt=xt, yt=yt,
                            input_queue=input_queue, o_received_event=o_received_event)
                input_queue.put('x')
                wait_move_ready(o_received_event)
                time.sleep(0.3)

        #什么都没有
        else:
            if class_ids == []:
                time.sleep(0.1)
            print('物品过少，无法判断')
            if often_list == [] or often_list[0] == '':
                pass
            else:
                use_skill_list(skill_list=often_list)
            check_sproom == 1
            time.sleep(0.1)

    read_yolo_result_1 = False
    sys.exit()
modelname = '../pt/auto-lypb-2.pt'
chenghao_number = 0
if __name__ == '__main__':
    print('流云瀑布_开始运行')
    # -----------------传递进来的参数提取---------------
    # 检查是否提供了足够的命令行参数
    if len(sys.argv) < 2:
        print("Usage: python example.py <variable_value>")
        sys.exit(1)
    # 获取第一个命令行参数（索引为1，因为sys.argv[0]是脚本名）
    qq = sys.argv[1]
    # 打印变量的值
    print(f"正在运行qq号为: {qq}")

    # -----------------启动串口管理线程---------------
    input_queue = multiprocessing.Queue()  # 用于主进程向子进程发送数据的队列
    o_received_event = multiprocessing.Event()  # 用于子进程通知主进程接收到'o'的事件
    # 启动子进程来管理串口
    process1 = multiprocessing.Process(target=read_serial_and_forward, args=(input_queue, o_received_event,))
    process1.start()
    print('开始启动串口管理子进程')
    # -----------------大写锁打开-----------------
    cap_lock_open()

    # -----------------确定窗口坐标-----------------
    windowx, windowy, width, height = init()

    # -----------------YOLO初始化----------------
    model = YOLO(modelname)
    im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
    results = model.predict(im)

    # -----------------速度基数确定-----------------
    xt, yt = speedtest_xy(model=model, windowx=windowx, windowy=windowy, width=width, height=height,
                          o_received_event=o_received_event, input_queue=input_queue, chenghao_number=chenghao_number)

    # ----------确定角色信息，开始标记，是否分解，技能释放--------------
    db_name=r'X:\predict\main\main_'+str(qq)+'.db'
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    # 寻找开始标记
    start_SN = find_breakpoint(qq, cursor)
    if start_SN == 0:
        print('查询不到')
        start_SN = 1
    else:
        print('中断序号为' + str(start_SN))
    # 获得信息
    row = use_SN_fand_inf(qq=qq, SN=start_SN, cursor=cursor)
    if row == 0:
        print('查询不到')
        time.sleep(600000)
    cursor.close()
    conn.close()

    # -----------------启动识别动作进程-----------------
    yolo_queue = multiprocessing.Queue()
    process3 = multiprocessing.Process(target=process_check, args=(
    yolo_queue, input_queue, o_received_event, xt, yt, windowx, windowy, width, height, row, qq))
    process3.start()

    # -----------------启动识别结果-----------------
    yolo_worker_result = {}
    while process3.is_alive():
        im = ImageGrab.grab(bbox=(windowx, windowy, windowx + width, windowy + height))
        results = model.predict(im)
        boxes = results[0].boxes
        # 提取
        class_ids = boxes.cls.cpu().numpy().astype(int).tolist()
        xyxy = boxes.xyxy.cpu().numpy().astype(int).tolist()
        xywh = boxes.xywh.cpu().numpy().astype(int).tolist()
        conf = boxes.conf.cpu().numpy().astype(float).tolist()
        # 复制
        class_ids_copy = class_ids[:]
        xyxy_copy = xyxy[:]
        xywh_copy = xywh[:]
        conf_copy = conf[:]
        # 字典化
        yolo_worker_result = {
            'class_ids': class_ids_copy,  # 边界框坐标
            'xyxy': xyxy_copy,  # 类别索引
            'xywh': xywh_copy,  # 这里假设我们还没有类别名称，可以后续添加
            'conf': conf_copy,  # 置信度
        }
        # 传递
        yolo_queue.put(yolo_worker_result)
        if qq=='1156711011' or qq=='1140103111':
            time.sleep(0.1)


    # -----------------结束程序关掉大写锁定-----------------
    cap_lock_close()

    # -----------------结束程序关掉子进程-----------------
    yolo_queue.put(None)
    print('读取识别结果进程已关闭')
    print('关掉串口管理进程')
    input_queue.put(None)
    time.sleep(1)
    if process3.is_alive:
        process3.terminate()
        time.sleep(3.5)
        print('截图、推断进程已关闭')
    print('清理yolo模型')
    del model
    #torch.cuda.empty_cache()

    print('退出程序')
    sys.exit()