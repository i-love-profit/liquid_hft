import argparse
import csv
import logging
import pytz
import time
import traceback
from datetime import datetime, timezone, timedelta
from quoine.client import Quoinex


def fetch_executions(timestamp, limit=1000, product_id=5):
    retry_count = 0
    while True:
        try:
            results = api.get_executions_since_time(product_id, timestamp, limit=limit)
            return [{"id": item["id"],
                     "timestamp": int(item["created_at"]),
                     "side": str(item["taker_side"]),
                     "price": float(item["price"]),
                     "size": float(item["quantity"])} for item in results]
        except Exception as e:
            retry_count += 1
            if retry_count <= 3:
                logger.warning("エラーが発生しました. 10秒待機して再トライします.")
                logger.warning(traceback.format_exc())
                time.sleep(10)
            else:
                logger.error("エラーが発生しました. 停止します.")
                raise e


if __name__ == "__main__":
    api = Quoinex("", "")
    jst = timezone(timedelta(hours=9), "JST")
    datetime_format = "%Y-%m-%d %H:%M:%S"
    header = ["timestamp", "datetime_jst", "open", "high", "low", "close", "volume", "buy_volume", "sell_volume",
              "first_execution_id", "last_execution_id"]
    # ロガー.
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())
    # コマンドライン引数.
    parser = argparse.ArgumentParser()
    now = datetime.now(pytz.UTC).replace(tzinfo=pytz.UTC).astimezone(jst)
    parser.add_argument("year", type=int, help=u"年", nargs="?", default=int(now.strftime("%Y")))
    parser.add_argument("month", type=int, help=u"月", nargs="?", default=int(now.strftime("%m")))
    parser.add_argument("day", type=int, help=u"日", nargs="?", default=int(now.strftime("%d")))
    args = parser.parse_args()
    # 開始時刻と終了時刻.
    start_date = datetime(args.year, args.month, args.day, 0, 0, 0, tzinfo=jst)
    start_timestamp = int(start_date.timestamp())
    end_date = start_date + timedelta(days=1)
    end_timestamp = int(end_date.timestamp())
    # OHLCVの作成.
    counter = 0
    ohlcv = dict()
    pre_timestamp = start_timestamp - 1
    while True:
        if counter % 10 == 0:
            now = datetime.fromtimestamp(start_timestamp, tz=jst).astimezone(jst).strftime(datetime_format)
            logger.debug(f"processing {now}...")
        if start_timestamp > end_timestamp:
            break
        executions = fetch_executions(start_timestamp)
        if len(executions) == 0:
            break
        for execution in executions:
            now_timestamp = execution['timestamp']
            price = execution["price"]
            while pre_timestamp != now_timestamp:
                close_price = ohlcv[pre_timestamp]["close"] if pre_timestamp in ohlcv else price
                close_id = ohlcv[pre_timestamp]["last_execution_id"] if pre_timestamp in ohlcv else ""
                pre_timestamp += 1
                datetime_jst = datetime.fromtimestamp(pre_timestamp, tz=jst).astimezone(jst).strftime(datetime_format)
                ohlcv[pre_timestamp] = {"timestamp": pre_timestamp, "datetime_jst": datetime_jst,
                                        "open": close_price,
                                        "high": close_price,
                                        "low": close_price,
                                        "close": close_price,
                                        "volume": 0,
                                        "buy_volume": 0,
                                        "sell_volume": 0,
                                        "first_execution_id": close_id,
                                        "last_execution_id": close_id}
            if ohlcv[now_timestamp]["volume"] == 0:
                ohlcv[now_timestamp]["open"] = price
                ohlcv[now_timestamp]["first_execution_id"] = execution["id"]
            if price > ohlcv[now_timestamp]["high"]:
                ohlcv[now_timestamp]["high"] = price
            if price < ohlcv[now_timestamp]["low"]:
                ohlcv[now_timestamp]["low"] = price
            ohlcv[now_timestamp]["close"] = price
            ohlcv[now_timestamp]["last_execution_id"] = execution["id"]
            if execution["side"] == "buy":
                ohlcv[now_timestamp]["buy_volume"] += execution["size"]
            if execution["side"] == "sell":
                ohlcv[now_timestamp]["sell_volume"] += execution["size"]
            ohlcv[now_timestamp]["volume"] += execution["size"]
        start_timestamp = executions[-1]['timestamp'] + 1
        time.sleep(1)  # 1分間に60回まで.
        counter += 1
    # ファイル出力.
    output_dir = ""
    output_filename = f"liquid_ohlcv_{args.year:0=4}{args.month:0=2}{args.day:0=2}.csv"
    output_encoding = "shift_jis"
    with open(output_dir + output_filename, "w", encoding=output_encoding) as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows([record.values() for record in ohlcv.values()])
