from pathlib import Path
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from typing import Optional
from time import sleep
from tqdm import tqdm
import json
import re
import requests


def create_filename(s: str) -> str:
    return re.sub(r"[^\w]+", "_", s)


# Input your course link directly here
course_url = input("[?] Enter course URL > ")
print(f"[i] Course files will be saved under 'downloads/json and downloads/videos'")
# not gonna bother allow changing the download path since it seems like mount is needed to use external storage in wsl
print(f"[i] Mount another directory to the downloads directory to change where the files are saved'")


class LeccapDownloader:
    driver: webdriver.Chrome
    download_path: Path

    def __init__(self, course_url: str) -> None:
        self.course_url = course_url
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("--user-data-dir=chrome-data")
        self.driver = webdriver.Chrome(options=chrome_options)

        self.download_path = (
            Path(__file__).parent / "downloads"
        )

    def close(self) -> None:
        self.driver.close()

    def go(self) -> None:
        self.download_course_link(self.course_url)

    def download_course_link(self, course_url: str) -> None:
        self.driver.get(course_url)
        sleep(1.0)
        while not course_url in self.driver.current_url:
            sleep(1.0) # Wait for the page to load fully
        play_buttons = self.driver.find_elements(
            by=By.CSS_SELECTOR,
            value='.play-link>a.btn[href^="/leccap/player/r/"]',
        )
        jsons = []
        for btn in tqdm(play_buttons, desc="Download JSON", leave=False):
            href = btn.get_attribute("href")
            assert href
            slug = href.split("/")[-1]
            res = self.driver.execute_async_script(
                f"""
                const callback = arguments[arguments.length - 1];
                fetch("/leccap/player/api/product/?rk={slug}")
                    .then(res => res.json())
                    .then(json => callback(json));
                """
            )
            jsons.append(res)

        def json_filename(j: dict) -> str:
            date_parts = j["date"].split("/")
            date = f"{date_parts[2]}-{date_parts[0]}-{date_parts[1]}"
            return create_filename(f"{date} {j['title']}")

        parent = self.download_path / "json"
        parent.mkdir(parents=True, exist_ok=True)
        for i, j in enumerate(jsons):
            with open(
                parent / f"{i+1:03}-{json_filename(j)}.json",
                "w",
            ) as f:
                f.write(json.dumps(j))

        print("[i] Downloading media. This may take a very long time...")

        def download_file(url: str, path: Path):
            response = requests.get(url, stream=True)
            total_size = int(response.headers.get("content-length", 0))
            block_size = 1024

            with tqdm(
                total=total_size,
                unit="B",
                unit_scale=True,
                leave=False,
                desc=path.name,
            ) as pb:
                with open(path, "wb") as f:
                    for data in response.iter_content(block_size):
                        pb.update(len(data))
                        f.write(data)

        parent = self.download_path / "videos"
        parent.mkdir(parents=True, exist_ok=True)
        for i, j in enumerate(tqdm(jsons)):
            url = f"https:{j['mediaPrefix']}{j['sitekey']}/{j['info']['products'][0]['movie_exported_name']}.mp4"
            video_filename = f"{i+1:03}-{json_filename(j)}.mp4"
            subtitle_filename = f"{i+1:03}-{json_filename(j)}.vtt"
            download_file(url, parent / video_filename)
            res = self.driver.execute_async_script(
                f"""
                const callback = arguments[arguments.length - 1];
                fetch("/leccap/player/api/webvtt/?rk={j['recordingkey']}")
                    .then(res => res.text())
                    .then(t => callback(t));
                """
            )
            with open(parent / subtitle_filename, "w") as f:
                f.write(res)


downloader = LeccapDownloader(course_url)
downloader.go()
downloader.close()
