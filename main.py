import os
import requests
import datetime
import time
import numpy as np
import json
import pandas as pd


test_urls = "https://api.binance.com/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=5"
test_urls2 = "/api/v3/avgPrice"  # 平均价格//////：
test_urls3 = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"  # 最新价格，可以同时获取多个
test_urls3 = "https://api.binance.comapi/v3/time"  # 获取服务器时间

headers = {
    "Content-Type": "application/json;charset=UTF-8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
}


def calculate_vwap_np(records):
    if len(records) != 168:
        return "未知"
    prices = np.array([(float(record["High_price"]) + float(record["Low_price"]) + float(record["Close_price"])) / 3 for record in records])
    volumes = np.array([float(record["Volume"]) for record in records])
    vwap = np.sum(prices * volumes) / np.sum(volumes)
    return vwap


def calculate_bollinger_bands_np(vwap, records, std_dev, std_dev2):
    if len(records) != 168:
        return "未知", "未知", "未知", "未知"
    high_std_dev = calculate_std_dev_np(records, "High_price")
    low_std_dev = calculate_std_dev_np(records, "Low_price")

    upper_band = vwap + std_dev * high_std_dev
    lower_band = vwap - std_dev * low_std_dev
    upper_band2 = vwap + std_dev2 * high_std_dev
    lower_band2 = vwap - std_dev2 * low_std_dev

    return upper_band, lower_band, upper_band2, lower_band2


# 用NumPy计算标准差的函数保持不变
def calculate_std_dev_np(records, price_key):
    prices = np.array([float(record[price_key]) for record in records])
    std_dev = np.std(prices)
    return std_dev


# 获取K线相关信息
def get_kline(urls):
    response_content = requests.get(url=urls, headers=headers)
    kline_contents = response_content.json()
    return kline_contents


# 获取币的实时价格
def get_price(url):
    response_content = requests.get(url=url, headers=headers)
    price = response_content.json().get("price")
    # price = response_content.json()
    return price


# 获取币安服务器的实时时间
def get_server_time():
    url_api = "https://api.binance.com/api/v3/time"
    response_content = requests.get(url=url_api, headers=headers)
    timestamp_milliseconds = response_content.json()["serverTime"]
    server_time = time_invert(int(timestamp_milliseconds))
    return server_time


def time_invert(timestamp_milliseconds):
    # 转换为秒级时间戳
    timestamp_seconds = timestamp_milliseconds / 1000
    # 然后进行相同格式化操作
    formatted_date = datetime.datetime.fromtimestamp(timestamp_seconds).strftime('%Y-%m-%d %H:%M:%S')
    return formatted_date


def get_data(coin, limit, Kline_level):
    get_price_api = f"https://api.binance.com/api/v3/ticker/price?symbol={coin}"
    get_Kline_api = f"https://api.binance.com/api/v3/klines?symbol={coin}&interval={Kline_level}&limit={limit}"
    # 获取coin的实时价格
    price = get_price(get_price_api)
    # 获取币安的服务器时间
    real_time = get_server_time()
    # 获取coin的k线相关信息
    Kline_contents = get_kline(get_Kline_api)

    data_dic = {}
    data_dic["real_time"] = real_time
    data_dic["coin"] = coin
    data_dic["real_price"] = price
    data_dic["level"] = Kline_level

    kline_lists = []
    for content in Kline_contents:
        dic = {}
        dic["Kline_open_time"] = time_invert(int(content[0]))
        dic["Open_price"] = content[1]
        dic["High_price"] = content[2]
        dic["Low_price"] = content[3]
        dic["Close_price"] = content[4]
        dic["Volume"] = content[5]
        dic["Kline_close_time"] = time_invert(int(content[6]))
        dic["Quote_asset_volume"] = content[7]
        dic["Number_of_trades"] = content[8]
        dic["Taker_buy_base_asset_volume"] = content[9]
        dic["Taker_buy_quote_asset_volume"] = content[10]
        kline_lists.append(dic)
    data_dic["Kline_data"] = kline_lists
    return data_dic


'''
现在是写的死循环，后续可以改成定时任务，比如每个小时刚刚开始的时候执行一次
'''
def main():
    coin_time = dict()
    coin_list = ["BTCUSDT", "LTCBTC", "BNBBTC", "ETHBTC"]
    for i in coin_list:
        coin_time[i] = 0
    Kline_level_list = ["1h","4h"]
    # Kline_level_name = ["1小时", "4小时"]
    K_num = 168
    while True:
        for c in coin_list:
            for i in range(len(Kline_level_list)):
                period = Kline_level_list[i]  # 将指定周期传入
                records = get_data(c, K_num, period)
                print('成功获取{}的{}根K线数据：'.format(c, len(records["Kline_data"])))
                time.sleep(1)

# 如果是新的柱子，那么开始用record进行支撑压力位计算
                if records["Kline_data"][-1]["Kline_close_time"] != coin_time[c]:
                    coin_time[c] = records["Kline_data"][-1]["Kline_close_time"]
                    now_price = records["Kline_data"][-1]["Close_price"]
                    str1 = "在最近一次计算中，" + c + " " + period + "" + "价格约为$" + str(now_price) + "。"

                    vwap = calculate_vwap_np(records["Kline_data"])
                    upper_band, lower_band, upper_band2, lower_band2 = calculate_bollinger_bands_np(vwap, records["Kline_data"], 2, 3)
                    # 打印结果
                    if period == "1h":

                        if float(now_price) > float(upper_band2):
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格上涨过猛，已远高于正常波动水平，请警惕回调，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                        elif float(now_price) > float(upper_band):
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格处于高位，上方压力位为{upper_band2}，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                        elif float(now_price) > float(vwap):
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格运行较为平稳，上方第一压力位为{upper_band}，第二压力位为{upper_band2}，下方第一支撑位为{vwap}（平均筹码价格水平，关键位置），第二支撑位为{lower_band}"
                        elif float(now_price) > float(lower_band):
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格运行较为平稳，上方第一压力位为{vwap}（平均筹码价格水平，关键位置），第二压力位为{upper_band}，下方第一支撑位为{lower_band}，第二支撑位为{lower_band2}"
                        elif float(now_price) > float(lower_band2):
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格处于低位，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置），下方支撑位为{lower_band2}"
                        else:
                            str2 = f"如果您是短线交易者，那么从短期来看，目前价格下跌急速，已远低于正常波动水平，随时可能止跌回升，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置）"

                        print(str1, str2)   # 此处传入数据库

                    elif period == "4h":

                        if float(now_price) > float(upper_band2):
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格上涨过猛，已远高于正常波动水平，请警惕回调，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                        elif float(now_price) > float(upper_band):
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格处于高位，上方压力位为{upper_band2}，下方第一支撑位为{upper_band}，第二支撑位为{vwap}（平均筹码价格水平，关键位置）"
                        elif float(now_price) > float(vwap):
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格运行较为平稳，上方第一压力位为{upper_band}，第二压力位为{upper_band2}，下方第一支撑位为{vwap}（平均筹码价格水平，关键位置），第二支撑位为{lower_band}"
                        elif float(now_price) > float(lower_band):
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格运行较为平稳，上方第一压力位为{vwap}（平均筹码价格水平，关键位置），第二压力位为{upper_band}，下方第一支撑位为{lower_band}，第二支撑位为{lower_band2}"
                        elif float(now_price) > float(lower_band2):
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格处于低位，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置），下方支撑位为{lower_band2}"
                        else:
                            str2 = f"如果您是中长线交易者，那么从中长期来看，目前价格下跌急速，已远低于正常波动水平，随时可能止跌回升，上方第一压力位为{lower_band}，第二压力位为{vwap}（平均筹码价格水平，关键位置）"

                        print(str1, str2)   # 此处传入数据库


if __name__ == '__main__':
    main()
