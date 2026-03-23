#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
百度贴吧爬虫 - 处理DOM回收机制
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json
import re


def clean_tieba_text(input_file, output_file=None):
    """
    清理贴吧文本文件，删除分隔线和楼层标记

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径（如果为None，则覆盖原文件）
    """
    if output_file is None:
        output_file = input_file.replace('.txt', '_cleaned.txt')

    print(f"\n正在清理文件: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    cleaned_lines = []
    removed_count = 0

    for line in lines:
        # 检查是否是分隔线（连续的-号，超过5个）
        if re.match(r'^-{5,}\s*$', line):
            removed_count += 1
            continue

        # 检查是否是楼层标记（【第X楼】开头）
        if re.match(r'^【第\d+楼】', line):
            removed_count += 1
            continue

        # 保留这一行
        cleaned_lines.append(line)

    # 保存清理后的内容
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)

    print(f"✓ 清理完成！删除了 {removed_count} 行，保留 {len(cleaned_lines)} 行")
    print(f"  清理后文件: {output_file}")

    return output_file

def crawl_tieba_post(url, output_file='tieba_content.txt', only_lz=True):
    """
    爬取百度贴吧帖子的所有文字内容

    Args:
        url: 贴吧帖子URL
        output_file: 输出文件名
        only_lz: 是否只看楼主（默认True）
    """
    # 初始化Chrome浏览器
    options = webdriver.ChromeOptions()
    # 如果不想看到浏览器窗口，可以取消下面这行的注释
    # options.add_argument('--headless')

    # 禁用一些不必要的功能以提高性能
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)

    try:
        print(f"正在打开页面: {url}")
        driver.get(url)

        # 最大化窗口以便更好地滚动
        driver.maximize_window()

        # 等待15秒让用户完成验证
        print("等待15秒以便完成验证...")
        time.sleep(15)

        # 额外等待页面内容加载
        print("等待页面内容加载...")
        try:
            # 尝试等待楼层容器出现
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, '.l_post')) > 0 or
                         len(d.find_elements(By.CSS_SELECTOR, 'div[class*="post"]')) > 0
            )
            print("页面内容已加载")
        except:
            print("等待超时，继续尝试...")

        # 点击"只看楼主"按钮
        if only_lz:
            print("\n尝试点击'只看楼主'按钮...")
            try:
                only_lz_btns = driver.find_elements(By.CSS_SELECTOR, '.lzl_link_unfold') or \
                              driver.find_elements(By.XPATH, "//*[contains(text(), '只看楼主')]") or \
                              driver.find_elements(By.CSS_SELECTOR, 'input[name="lz_only"]')

                if only_lz_btns:
                    only_lz_btns[0].click()
                    print("已点击'只看楼主'")
                    time.sleep(2)  # 等待页面刷新
                else:
                    print("未找到'只看楼主'按钮，继续...")
            except Exception as e:
                print(f"点击'只看楼主'失败: {e}")

        # 用于存储所有楼层的内容
        collected_posts = []

        print("=" * 60)
        print("开始爬取楼层内容...")
        print("=" * 60)

        # 用于记录已收集的楼层内容，避免重复
        collected_texts = set()
        scroll_count = 0
        no_new_content_count = 0
        max_no_new_count = 5  # 连续5次没有新内容就停止

        while True:
            scroll_count += 1
            print(f"\n--- 第 {scroll_count} 次滚动 ---")

            # 尝试多种选择器来找到楼层容器
            post_containers = []
            selectors_to_try = [
                '.pb-content-item',  # 新版百度贴吧
                '.l_post',           # 旧版百度贴吧
                'div[data-field]',   # 旧版备用
            ]

            for selector in selectors_to_try:
                post_containers = driver.find_elements(By.CSS_SELECTOR, selector)
                if post_containers:
                    print(f"使用选择器 '{selector}' 找到 {len(post_containers)} 个楼层容器")
                    break

            if not post_containers:
                print("未找到任何楼层容器！")
                # 保存调试信息
                with open('page_source_debug.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("页面源代码已保存到 page_source_debug.html")
                break

            current_batch_count = 0

            # 遍历每个楼层容器
            for idx, container in enumerate(post_containers):
                try:
                    # 获取容器的所有文本内容
                    text = container.text.strip()

                    # 过滤掉一些无用信息
                    if not text or len(text) < 10:
                        continue
                    if '首页' in text and '大家都在逛的吧' in text:  # 跳过侧边栏
                        continue
                    if '百度版权声明' in text:  # 跳过页脚
                        continue
                    if '搜索吧或者贴子' in text:  # 跳过搜索框
                        continue
                    if '登录' in text and '注册' in text and len(text) < 50:  # 跳过登录框
                        continue

                    # 使用文本作为去重key（因为新版贴吧可能没有唯一ID）
                    text_key = text[:100]  # 使用前100个字符作为key
                    if text_key in collected_texts:
                        continue

                    collected_texts.add(text_key)

                    # 尝试提取楼层信息（可能在文本中或属性中）
                    floor_num = idx + 1
                    author_name = "未知用户"

                    # 尝试从文本中提取作者和楼层信息
                    lines = text.split('\n')
                    if len(lines) > 1:
                        # 第一行可能是作者名或标题
                        first_line = lines[0].strip()
                        if len(first_line) < 30:  # 可能是作者名
                            author_name = first_line

                    # 保存楼层信息
                    collected_posts.append({
                        'floor': floor_num,
                        'author': author_name,
                        'content': text,
                        'text_key': text_key
                    })

                    current_batch_count += 1
                    print(f"  ✓ 收集第 {floor_num} 个: {author_name} - {text[:50]}...")

                except Exception as e:
                    # 静默处理单个楼层错误
                    continue

            print(f"本次滚动收集到 {current_batch_count} 条新内容，累计 {len(collected_posts)} 条")

            # 如果本次没有收集到新内容
            if current_batch_count == 0:
                no_new_content_count += 1
                print(f"连续 {no_new_content_count}/{max_no_new_count} 次没有新内容")
                if no_new_content_count >= max_no_new_count:
                    print("连续多次没有新内容，爬取完成")
                    break
            else:
                no_new_content_count = 0  # 重置计数器

            # 尝试多种滚动方式
            # 方法1：滚动到页面底部
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)

            # 方法2：滚动最后一个楼层容器到可视区域
            if post_containers:
                try:
                    last_container = post_containers[-1]
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'end'});", last_container)
                    print(f"已滚动到第 {len(post_containers)} 个容器")
                except:
                    pass

            # 方法3：使用Page Down键
            try:
                from selenium.webdriver.common.keys import Keys
                body = driver.find_element(By.TAG_NAME, 'body')
                body.send_keys(Keys.PAGE_DOWN)
                body.send_keys(Keys.PAGE_DOWN)
            except:
                pass

            # 等待页面加载新内容
            print("等待新内容加载...")
            time.sleep(3)

            # 检查是否已经到达页面底部
            page_height = driver.execute_script("return document.body.scrollHeight")
            current_pos = driver.execute_script("return window.pageYOffset + window.innerHeight")

            print(f"页面高度: {page_height}, 当前位置: {current_pos}")

            if current_pos >= page_height - 200:  # 距离底部200像素以内
                print("已接近页面底部，再尝试2次...")
                no_new_content_count += 1

            # 最多滚动150次，防止无限循环
            if scroll_count >= 150:
                print("达到最大滚动次数，停止爬取")
                break

        print(f"\n爬取完成！共收集 {len(collected_posts)} 个楼层")

        # 保存原始文件
        raw_file = output_file.replace('.txt', '_raw.txt')
        print(f"\n正在保存原始文件: {raw_file}")
        with open(raw_file, 'w', encoding='utf-8') as f:
            f.write(f"百度贴吧帖子内容\n")
            f.write(f"URL: {url}\n")
            f.write(f"爬取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"共收集 {len(collected_posts)} 个楼层\n")
            f.write("=" * 80 + "\n\n")

            for post in collected_posts:
                f.write(f"【第{post['floor']}楼】 {post['author']}\n")
                f.write(f"{post['content']}\n")
                f.write("-" * 80 + "\n\n")

        # 同时保存JSON格式
        json_file = output_file.replace('.txt', '.json')
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(collected_posts, f, ensure_ascii=False, indent=2)

        print(f"✓ 原始文件保存完成: {raw_file}")
        print(f"✓ JSON文件保存完成: {json_file}")

        # 自动清理文本文件
        cleaned_file = clean_tieba_text(raw_file, output_file)

        print(f"\n" + "=" * 60)
        print(f"✓ 全部完成！")
        print(f"  原始文件: {raw_file}")
        print(f"  清理文件: {cleaned_file}")
        print(f"  JSON文件: {json_file}")
        print(f"  共收集 {len(collected_posts)} 个楼层")
        print("=" * 60)

    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # 关闭浏览器
        print("\n按回车键关闭浏览器...")
        input()
        driver.quit()


if __name__ == "__main__":
    # 目标URL
    url = "https://tieba.baidu.com/p/4989988691?fr=personpage"

    # 开始爬取
    # only_lz=True 表示只看楼主，False 表示看所有楼层
    crawl_tieba_post(url, output_file='tieba_4989988691.txt', only_lz=True)
