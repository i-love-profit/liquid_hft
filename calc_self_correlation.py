import argparse
import logging
import pandas as pd
import pytz
from datetime import datetime, timezone, timedelta
from matplotlib import pyplot as plt
from numpy import corrcoef


if __name__ == "__main__":
    jst = timezone(timedelta(hours=9), "JST")
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
    # CSV読み込み.
    input_dir = ""
    input_filename = f"liquid_ohlcv_{args.year:0=4}{args.month:0=2}{args.day:0=2}.csv"
    input_encoding = "shift_jis"
    output_dir = ""
    output_filename = f"liquid_ohlcv_{args.year:0=4}{args.month:0=2}{args.day:0=2}.png"
    csv = pd.read_csv(input_dir + input_filename, encoding=input_encoding)
    # 相関計算.
    second = 1
    open_prices = csv.open.values
    past_returns = []
    future_returns = []
    for index in range(second, len(open_prices) - second):
        past_returns.append(open_prices[index] - open_prices[index - second])
        future_returns.append(open_prices[index + second] - open_prices[index])
    correlation = corrcoef(past_returns, future_returns)
    r2 = correlation[0][1] ** 2
    # グラフ出力.
    title = f"Correlation {args.year}/{args.month}/{args.day}"
    fig = plt.figure()
    fig.suptitle(title)
    ax = fig.add_subplot(111)
    ax.scatter(past_returns, future_returns, c="blue", s=20, edgecolors="blue", alpha=0.3)
    ax.set_xlabel(f"Past {second} seconds return [yen]")
    ax.set_ylabel(f"Future {second} seconds return [yen]")
    ax.grid(which="major", axis="x", color="gray", alpha=0.5, linestyle="dotted", linewidth=1)
    ax.grid(which="major", axis="y", color="gray", alpha=0.5, linestyle="dotted", linewidth=1)
    ax.text(0.8, 0.1, f"R**2={r2:.4f}", transform=ax.transAxes)
    plt.savefig(output_dir + output_filename)
