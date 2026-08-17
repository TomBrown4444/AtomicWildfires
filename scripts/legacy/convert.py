import pandas as pd

df = pd.read_csv("fire_nrt_J2V-C2_767689.csv")
# acq_time is HHMM as an int; zero-pad to 4 digits
t = df["acq_time"].astype(int).astype(str).str.zfill(4)
df["acq_datetime"] = pd.to_datetime(
    df["acq_date"] + "T" + t.str[:2] + ":" + t.str[2:] + ":00"
).dt.strftime("%Y-%m-%dT%H:%M:%S")

df.to_csv("russia_fires_timestamped.csv", index=False)