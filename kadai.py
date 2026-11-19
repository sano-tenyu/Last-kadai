import time
import sqlite3
import requests
from bs4 import BeautifulSoup


BASE_URL = "https://github.com/orgs/google/repositories"
DB_FILE = "google_repositories.db"


# SQLite準備
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute("""DROP TABLE IF EXISTS repositories;""")

cur.execute("""
    CREATE TABLE repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repository_name TEXT UNIQUE,
        language TEXT,
        stars TEXT
    );
""")

conn.commit()


# requestsのセッションを作成
session = requests.Session()

# 普通のブラウザからのアクセスに近い情報を付ける
session.headers.update({
    "User-Agent":
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/140.0 Safari/537.36"
})


# ページ巡回
page_number = 1

while True:
    print(f"\n----- {page_number}ページ目 -----")

    # GitHubの現在のURL形式
    params = {
        "q": "",
        "type": "all",
        "language": "",
        "sort": "name",
        "page": page_number
    }

    print("アクセス中:", BASE_URL, params)


    # 取得(最大3回再試行)
    retry = 0
    repo_links = []

    while retry < 3:

        # githubのアクセス制限 （Too Many Requests）回避のため(1)でなく(３)に
        time.sleep(3)

        response = session.get(BASE_URL, params=params, timeout=30)

        print("HTTP:", response.status_code, "実際のURL:", response.url)

        # 200以外
        if response.status_code != 200:
            retry += 1

            print(f"取得失敗。再試行 {retry}/3")

            time.sleep(5)

            continue

        soup = BeautifulSoup(response.content, "html.parser")


        # リポジトリリンク抽出
        repo_links = []

        for a in soup.select('a[href^="/google/"]'):

            href = a.get("href","")
            parts = (
                href
                .strip("/")
                .split("/")
            )

            if (
                len(parts) == 2
                and parts[0] == "google"
            ):

                repo_links.append(a)


        # リポジトリが見つかった
        if len(repo_links) > 0:
            break

        # 0件の場合
        retry += 1

        print(
            f"リポジトリが0件でした。"
            f"再試行 {retry}/3"
        )


        # デバッグ情報
        print(
            "ページタイトル:",
            soup.title.get_text(
                strip=True
            )
            if soup.title
            else "なし"
        )


        # 少し長めに待つ
        time.sleep(5 * retry)


    # 3回試しても0件
    if len(repo_links) == 0:

        print("3回試してもリポジトリを取得できませんでした。")
        print("停止したページ:", page_number)
        print("停止URL:",response.url)

        break

    print("このページのリポジトリ数:", len(repo_links))


    # リポジトリ情報取得
    for a in repo_links:

        # リポジトリ名
        name = a.get_text(strip=True)

        repo_block = a.find_parent("li")

        if repo_block is None:
            continue

        # 主要言語

        language_tag = repo_block.find(
            "span",
            class_=lambda c:
                c
                and "PrimaryLanguageName"
                in c
        )


        if language_tag is not None:

            language = (language_tag.get_text(strip=True))

        else:
            language = ""


        # スター数
        star_tag = (
            repo_block.select_one(
                'a[href$="/stargazers"]'
            )
        )
        
        if star_tag is not None:

            stars = (
                star_tag
                .get_text(strip=True)
            )

        else:

            stars = "0"

        
        # DB保存
        cur.execute("""
            INSERT OR REPLACE
            INTO repositories
            (
                repository_name,
                language,
                stars
            )
            VALUES (?, ?, ?);
        """, (
            name,
            language,
            stars
        ))


        print(name, language, stars)

    conn.commit()

    # DB件数
    count = cur.execute("""
        SELECT COUNT(*)
        FROM repositories;
    """).fetchone()[0]

    print(
        "現在のDB保存件数:",
        count
    )

    # 最終ページ判定。通常は1ページ30件。30件未満なら最終ページと判断。•
    if len(repo_links) < 30:

        print( "30件未満のため最終ページと判断します。")

        break


    # 次のページ
    page_number += 1


# 最終確認
count = cur.execute("""
    SELECT COUNT(*)
    FROM repositories;
""").fetchone()[0]


print("\n======================")
print("スクレイピング完了")
print(
    "実際にDBへ保存された件数:",
    count
)
print("======================")


# SELECT
rows = cur.execute("""
    SELECT
        repository_name,
        language,
        stars
    FROM repositories;
""")


for row in rows:
    print(row)


conn.close()