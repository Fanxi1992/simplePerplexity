import json
import time
from datetime import datetime
import numpy as np

np.set_printoptions(suppress=True)  # 取消科学计数法
import pandas as pd
import requests
import _thread


# 定义一个线程，用来发送信息到数据库
class DingTalk_Base:
    def __init__(self):
        self.__headers = {'Content-Type': 'application/json;charset=utf-8'}
        self.url = ''

    def send_msg(self, text):
        json_text = {
            "msgtype": "text",
            "text": {
                "content": text
            }
        }
        try:
            requests.post(self.url, json.dumps(json_text), headers=self.__headers,
                          timeout=10)  # requests.post(self.url, json.dumps(json_text), headers=self.__headers, timeout=10)
        except requests.exceptions.RequestException as e:
            Log(f"发送消息失败: {e}")


class DingTalk_Disaster_3(DingTalk_Base):
    def __init__(self):
        super().__init__()
        self.url = 'http://127.0.0.1:2222/your_endpoint'


def ding_log():
    global log_list

    ding = DingTalk_Disaster_3()

    while True:

        if len(log_list) != 0:
            ding.send_msg(log_list[0])
            del log_list[0]
            Sleep(300)
        else:
            Sleep(300)


def Log_def(msg1, msg2):
    global log_list
    msg_info = str(msg1) + str(msg2)
    log_list.append(msg_info)
    Log(msg_info)


def calculate_vwap_np(records):
    if len(records) != 168:
        return "未知"
    prices = np.array([(record["High"] + record["Low"] + record["Close"]) / 3 for record in records])
    volumes = np.array([record["Volume"] for record in records])
    vwap = np.sum(prices * volumes) / np.sum(volumes)
    return vwap


def calculate_bollinger_bands_np(vwap, records, std_dev, std_dev2):
    if len(records) != 168:
        return "未知", "未知", "未知", "未知"
    high_std_dev = calculate_std_dev_np(records, "High")
    low_std_dev = calculate_std_dev_np(records, "Low")

    upper_band = vwap + std_dev * high_std_dev
    lower_band = vwap - std_dev * low_std_dev
    upper_band2 = vwap + std_dev2 * high_std_dev
    lower_band2 = vwap - std_dev2 * low_std_dev

    return upper_band, lower_band, upper_band2, lower_band2


# 用NumPy计算标准差的函数保持不变
def calculate_std_dev_np(records, price_key):
    prices = np.array([record[price_key] for record in records])
    std_dev = np.std(prices)
    return std_dev


# 定义指代具体币种和周期，方便后续调用生成文本
class mytrade():
    def __init__(self, symbol_code):
        self.symbol = symbol_code
        self.period_list = [1 * 60 * 60, 4 * 60 * 60]  # 定义四个周期
        self.period_name_list = ["1h", "4h"]  # 定义2个周期的名字
        self.last_time_list = []  # 存储每个周期下最新柱子的时间
        exchange.SetCurrency(self.symbol)  # 传入指定币种交易对（修改添加）
        for period in self.period_list:
            records = _C(exchange.GetRecords, period)
            self.last_time_list.append(records[-1]["Time"])  # 将最新的一根柱子的时间加入
            Sleep(200)

    # 定义主程序poll，任务是循环指定币种各周期，对计算出的最新的VWAP和上下界，基于符号和周期生成文本append到loglist中，同步输出给服务器
    def poll(self):
        exchange.SetCurrency(self.symbol)  # 传入指定币种交易对
        exchange.SetMaxBarLen(168)  # 设置最大获取柱子数
        for i in range(len(self.period_list)):  # 对每个周期进行循环
            Sleep(200)
            period = self.period_list[i]  # 将指定周期传入
            period_name = self.period_name_list[i]  # 文本用这个表示周期
            records = _C(exchange.GetRecords, period)  # 获取该周期的K线数据
            print('成功获取{}的{}根K线数据：'.format(self.symbol, len(records)))

            if records[-1]["Time"] != self.last_time_list[i]:  # 检测是否到了新柱子了，如果到了，就更新时间，并开始获取指标值并判断
                self.last_time_list[i] = records[-1]["Time"]
                now_price = records[-1]["Close"]  # 最新一次计算的时候，币种的价格now_price
                str1 = "在最近一次计算中，" + self.symbol + " " + period_name + "" + "价格约为$" + str(now_price) + "。"

                # 使用示例
                vwap = calculate_vwap_np(records)
                upper_band, lower_band, upper_band2, lower_band2 = calculate_bollinger_bands_np(vwap, records, 2, 3)
                # 打印结果
                if period_name == "1h":

                    if now_price > upper_band2:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格上涨过猛，已远高于正常波动水平，请警惕回调，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                    elif now_price > upper_band:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格处于高位，上方压力位为{upper_band2}，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                    elif now_price > vwap:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格运行较为平稳，上方第一压力位为{upper_band}，第二压力位为{upper_band2}，下方第一支撑位为{vwap}（平均筹码价格水平，关键位置），第二支撑位为{lower_band}"
                    elif now_price > lower_band:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格运行较为平稳，上方第一压力位为{vwap}（平均筹码价格水平，关键位置），第二压力位为{upper_band}，下方第一支撑位为{lower_band}，第二支撑位为{lower_band2}"
                    elif now_price > lower_band2:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格处于低位，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置），下方支撑位为{lower_band2}"
                    else:
                        str2 = f"如果您是短线交易者，那么从短期来看，目前价格下跌急速，已远低于正常波动水平，随时可能止跌回升，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置）"

                    Log_def(str1, str2)

                elif period_name == "4h":

                    if now_price > upper_band2:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格上涨过猛，已远高于正常波动水平，请警惕回调，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                    elif now_price > upper_band:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格处于高位，上方压力位为{upper_band2}，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                    elif now_price > vwap:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格运行较为平稳，上方第一压力位为{upper_band}，第二压力位为{upper_band2}，下方第一支撑位为{vwap}（平均筹码价格水平，关键位置），第二支撑位为{lower_band}"
                    elif now_price > lower_band:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格运行较为平稳，上方第一压力位为{vwap}（平均筹码价格水平，关键位置），第二压力位为{upper_band}，下方第一支撑位为{lower_band}，第二支撑位为{lower_band2}"
                    elif now_price > lower_band2:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格处于低位，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置），下方支撑位为{lower_band2}"
                    else:
                        str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格下跌急速，已远低于正常波动水平，随时可能止跌回升，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置）"

                    Log_def(str1, str2)


def main():
    global log_list

    log_list = ['sdfsfsdfsdfdfsd']

    try:
        _thread.start_new_thread(ding_log, ())  # VPS服务器上测试
    except Exception as e:
        Log("错误信息：", e)
        raise Exception("stop")

    # ~修改
    trade_list = []  # 实例列表

    symbol_code_list = symbol_input.split(",")  # 初始化自定义币种设置，以,间隔，输入列表

    for symbol_code in symbol_code_list:
        trade_class = mytrade(symbol_code)  # 对每一个输入的币种做mytrade实例化，赋予该币种各种属性，如周期等

        trade_list.append(trade_class)  # 将每一个实例化的币种对象加入实例列表

    # ~开始主程序

    while True:  # 一直循环

        for trade_class1 in trade_list:
            trade_class1.poll()  # 将实例列表中的每一个实例化的币种运行主程序poll



