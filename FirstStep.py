#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
融优课堂自动播放视频脚本 v2.1 (无 undetected-chromedriver)
------------------------------
使用标准 selenium + webdriver-manager，自动管理 ChromeDriver 版本。
基础防检测参数已添加，适用于检测不严格的网站。
"""

import time
import os
import sys
import random
from datetime import datetime

# ==================== 自动安装依赖 ====================
try:
    from selenium import webdriver
except ImportError:
    print("[INFO] 安装 selenium...")
    os.system(f"{sys.executable} -m pip install selenium -q")
    from selenium import webdriver

try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    print("[INFO] 安装 webdriver-manager...")
    os.system(f"{sys.executable} -m pip install webdriver-manager -q")
    from webdriver_manager.chrome import ChromeDriverManager

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

# ==================== 配置区域（✏️ 请根据实际页面修改） ====================
# 课程主页 URL（例如你进入某个课程后的页面）
COURSE_URL = "https://livedu.com.cn/ispace4.0/moocxsxx/queryAllZjByKcdm.do"

# 【重要】章节列表的 CSS 选择器，用于自动点击进入各个章节
CHAPTER_SELECTOR = ".chapter-item a, .section-item a, .lesson-link, ul.catalog li a"

# 视频元素选择器
VIDEO_SELECTOR = "video, .video-js, .jw-video"

# “下一节”按钮的文本关键词
NEXT_BUTTON_KEYWORDS = ["下一", "下一节", "下一章", "下一个", "Next"]

# 暂停检测弹窗中的文本关键词
PAUSE_CONFIRM_KEYWORDS = ["继续", "确定", "我知道了", "关闭", "忽略"]

# 每个视频播完后的额外等待时间（秒）
POST_PLAY_WAIT = 3

# 检查视频是否结束的间隔（秒）
CHECK_INTERVAL = 2

# 如果获取不到视频时长，最多等待多少秒后强制结束
MAX_WAIT_IF_NO_DURATION = 600   # 10分钟

# 是否使用已保存的 Chrome 用户数据（第一次登录后自动保存，下次免登录）
USE_PROFILE = False
PROFILE_PATH = "C:/Users/你的用户名/AppData/Local/Google/Chrome/User Data"
# ================================================================


def log(msg):
    """带时间戳的日志输出"""
    t = datetime.now().strftime("%H:%M:%S")
    print(f"[{t}] {msg}")


def human_wait(sec):
    """模拟人类微小延迟"""
    time.sleep(sec + random.uniform(-0.3, 0.5))


def skip_pause_dialogs(driver):
    """扫描并关闭所有可能的暂停检测弹窗"""
    for keyword in PAUSE_CONFIRM_KEYWORDS:
        try:
            xpath = f"//*[self::button or self::a or self::span][contains(text(), '{keyword}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    log(f"    ↪ 关闭弹窗: {keyword}")
                    driver.execute_script("arguments[0].click();", el)
                    time.sleep(1.5)
        except:
            pass


def find_and_play_videos(driver):
    """在当前页面查找所有视频并依次播放"""
    log("查找页面中的视频元素...")
    try:
        videos = driver.find_elements(By.CSS_SELECTOR, VIDEO_SELECTOR)
        if not videos:
            videos = driver.find_elements(By.XPATH, "//video | //*[contains(@class,'video-js')]")
    except:
        videos = []

    if not videos:
        log("⚠️ 未找到视频元素，请检查选择器。")
        return False

    log(f"✅ 找到 {len(videos)} 个视频，开始顺序播放")
    for idx, video in enumerate(videos, 1):
        log(f"--- 播放第 {idx} 个视频 ---")
        try:
            # 滚动到视频位置
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", video)
            human_wait(1.5)

            # 尝试多种方式触发播放
            try:
                driver.execute_script("arguments[0].play();", video)
                log("    [JS play] 已触发")
            except:
                try:
                    driver.execute_script("arguments[0].click();", video)
                    log("    [click] 已触发")
                except:
                    play_btn = video.find_element(By.XPATH, ".//*[contains(@class,'play')] | .//*[contains(@class,'vjs-big-play-button')]")
                    driver.execute_script("arguments[0].click();", play_btn)
                    log("    [播放按钮 click] 已触发")

            human_wait(2)

            # 获取视频时长
            duration = None
            try:
                duration = driver.execute_script("return arguments[0].duration", video)
                if duration:
                    log(f"    📺 视频时长: {duration:.1f} 秒")
            except:
                pass

            # 等待视频播放结束
            start_time = time.time()
            last_known_time = 0
            stable_count = 0

            while True:
                human_wait(CHECK_INTERVAL)
                skip_pause_dialogs(driver)

                try:
                    current = driver.execute_script("return arguments[0].currentTime", video)
                    if current is None:
                        continue

                    if duration and current >= duration - 1:
                        log(f"    ✅ 视频播放完成 ({current:.1f}/{duration:.1f})")
                        break

                    # 如果 currentTime 30 秒内没变化，认为卡住
                    if current == last_known_time:
                        stable_count += 1
                    else:
                        stable_count = 0

                    if stable_count > 15:  # 30秒无变化
                        log("    ⚠️ 播放进度无变化，跳过此视频")
                        break

                    last_known_time = current
                except:
                    pass

                elapsed = time.time() - start_time
                if duration and elapsed > duration + 60:
                    log("    ⏰ 播放超时，强制结束")
                    break
                if not duration and elapsed > MAX_WAIT_IF_NO_DURATION:
                    log("    ⏰ 无时长超时保护触发")
                    break

            time.sleep(POST_PLAY_WAIT)

        except Exception as e:
            log(f"    ❌ 播放视频时出错: {e}")
            continue

    return True


def click_next_button(driver):
    """尝试点击‘下一节’按钮"""
    for kw in NEXT_BUTTON_KEYWORDS:
        try:
            xpath = f"//*[self::a or self::button or self::span][contains(text(), '{kw}')]"
            elements = driver.find_elements(By.XPATH, xpath)
            for el in elements:
                if el.is_displayed() and el.is_enabled():
                    driver.execute_script("arguments[0].click();", el)
                    log(f"    ➡️ 点击「{kw}」按钮，跳转下一节")
                    time.sleep(4)   # 等待页面加载
                    return True
        except:
            pass
    log("    ℹ️ 未找到下一节按钮")
    return False


def traverse_chapters(driver):
    """遍历所有章节并播放视频"""
    log("扫描章节列表...")
    try:
        chapter_links = driver.find_elements(By.CSS_SELECTOR, CHAPTER_SELECTOR)
        if not chapter_links:
            chapter_links = driver.find_elements(By.XPATH, "//a[contains(@href,'queryAllZj')]")
    except:
        chapter_links = []

    if not chapter_links:
        log("📌 未找到章节列表，将只处理当前页面")
        find_and_play_videos(driver)
        click_next_button(driver)
        return

    log(f"📚 发现 {len(chapter_links)} 个章节/课程链接")
    for i, link in enumerate(chapter_links, 1):
        try:
            title = link.text.strip() or f"第{i}章"
            log(f"\n{'='*50}")
            log(f"📖 进入章节 [{i}/{len(chapter_links)}]: {title}")

            # 点击章节链接
            driver.execute_script("arguments[0].click();", link)
            time.sleep(3)

            # 处理可能的弹窗
            skip_pause_dialogs(driver)

            # 播放视频
            find_and_play_videos(driver)

            # 尝试点击下一节
            click_next_button(driver)

        except Exception as e:
            log(f"❌ 处理章节时出错: {e}")
            continue


def main():
    log("🚀 启动融优课堂自动播放器 v2.1")
    log("正在使用标准 selenium + webdriver-manager...")

    # 配置 Chrome 选项
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if USE_PROFILE:
        options.add_argument(f"--user-data-dir={PROFILE_PATH}")
        log("📁 使用已保存的用户数据（免登录）")

    # 自动获取并设置 ChromeDriver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # 隐藏自动化特征（通过 JS 修改 navigator.webdriver）
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })

    try:
        driver.get(COURSE_URL)
        log(f"🌐 打开课程主页: {COURSE_URL}")

        if not USE_PROFILE:
            log("🔐 请手动登录，登录后按回车键继续...")
            input("   按回车键开始自动播放 >>> ")

        log("⏳ 等待页面加载...")
        time.sleep(3)

        traverse_chapters(driver)

        log("\n✅ 全部视频播放完毕！")

    except Exception as e:
        log(f"❌ 主程序错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        log("\n💡 输入 'q' 退出浏览器，直接回车重新检查页面...")
        cmd = input(" >>> ")
        if cmd.strip().lower() == 'q':
            driver.quit()
            log("👋 退出。")
        else:
            traverse_chapters(driver)


if __name__ == "__main__":
    main()