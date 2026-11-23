# 空の劇場 (Sky Theater)

M5Stack StopWatch が、国際宇宙ステーション（ISS）の見える通過を「今夜の公演」として知らせる仕組みです。

- 夕方、時計が今夜の番組（通過の時刻・方角・高さ）を声で読み上げます
- 開演5分前に振動と声で知らせます
- 通過中は、地球の影に入って光が消える場面などを声で案内します
- 終演すると観察スタンプが1つ増えます
- 曇りの日は中止になります

## 仕組み

```
CelesTrak (TLE) --+--> PC / GitHub Actions: 通過計算 (SGP4)
Open-Meteo (雲量) --+        番組表 program.json を生成
VOICEVOX (任意)  ------> 読み上げ音声 WAV を生成
                              |
                    GitHub Pages で公開
                              |
              StopWatch が Wi-Fi で取得し、時刻どおりに再生
```

通過の判定は「ISSに太陽光が当たっていて、観測地が暗く、十分な高さまで上がる」区間だけを切り出します。ISSは地平線上の最高点に届く前に地球の影に入って消えることが多いため、見える区間の中での最高高度を番組に使います。京田辺での計算結果は Heavens-Above の通過表と照合済みです（時刻は数十秒以内、高度は1度前後で一致）。

## 使い方（PC側）

```bash
pip install -r requirements.txt
cp config.example.json config.json   # 観測地点の緯度経度を自分の場所に書き換える
python -m skytheater.run --config config.json --out docs
```

`docs/program.json` が生成されます。読み上げ音声も作る場合（VOICEVOXエンジンを起動しておく）:

```bash
python -m skytheater.run --config config.json --out docs --audio
```

## ずっと運用する形

- GitHub Actions のワークフローが毎日、最新の軌道データで番組表を再計算し、`docs/` にコミットします。有効にするには、リポジトリ直下の `update.yml.example` を `.github/workflows/update.yml` として置いてください（GitHubの画面から新規ファイルとして作成できます）
- GitHub Pages を `docs/` フォルダで有効にすると、時計はそこから番組表と音声を取得できます
- 軌道データ（TLE）は数日で古くなるため、この日次更新が前提です

## 時計側

`watch/sky_theater_watch.ino`（Arduino / M5Unified 向けの雛形）:

- Wi-Fiで `program.json` と音声を取得し、内蔵フラッシュに保存します
- イベント時刻に振動と音声再生をします
- スタンプ数を数えます

`PROGRAM_BASE_URL` と Wi-Fi 設定を自分の環境に書き換えてください。雛形のうち振動モーターと音声再生の細部は、実機ビルド時にライブラリに合わせて調整が必要です。

## 設定 (config.json)

| 項目 | 意味 |
|---|---|
| `observer.lat/lon/alt_m` | 観測地点 |
| `observer.tz_name` | タイムゾーン（例 `Asia/Tokyo`） |
| `thresholds.min_peak_el` | 番組にする最低の最高高度（度） |
| `thresholds.cloud_cancel_pct` | この雲量（%）を超えたら中止 |
| `days` | 何日先まで計算するか |

## データとライセンス

- 軌道データ: [CelesTrak](https://celestrak.org) の TLE
- 雲量: [Open-Meteo](https://open-meteo.com)（APIキー不要）
- コード: MIT License
- 読み上げ音声は配布していません。各利用者が自分の VOICEVOX で生成してください。生成した音声を公開する場合は、VOICEVOX と使用する音声ライブラリ（例: ずんだもん）の利用規約（クレジット表記など）に従ってください

## English (brief)

Sky Theater turns visible ISS passes into a nightly "show" on an M5Stack StopWatch: an evening announcement, a 5-minute warning with vibration, live narration as the ISS crosses and disappears into Earth's shadow, and an observation stamp at the end. Passes are computed from CelesTrak TLE data with SGP4; cloud cover comes from Open-Meteo. A GitHub Actions workflow refreshes the program daily and GitHub Pages serves it to the watch. Set your location in `config.json` and run `python -m skytheater.run`.
