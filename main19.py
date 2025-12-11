# -*- coding: utf-8 -*-
from kivy.lang import Builder
from kivymd.app import MDApp
from kivymd.uix.card import MDCard
from kivymd.uix.list import ILeftBody, OneLineListItem
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.dialog import MDDialog
from kivymd.uix.button import MDFlatButton
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.textfield import MDTextField
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, BooleanProperty
from kivy.core.text import LabelBase
from kivy.animation import Animation
import requests
import json
import time
import random
from datetime import datetime
from retrying import retry
import os
import traceback

# 注册中文字体 - 按优先级尝试多个字体
font_paths = [
    'msyh.ttc',           # 微软雅黑
    'simhei.ttf',         # 黑体  
    'simsun.ttc',         # 宋体
    'NotoSansSC-Regular.ttf',  # Noto Sans SC
]

registered_font = False
for font_path in font_paths:
    if os.path.exists(font_path):
        try:
            LabelBase.register('ChineseFont', font_path)
            registered_font = True
            print(f"成功注册字体: {font_path}")
            break
        except Exception as e:
            print(f"注册字体失败 {font_path}: {e}")

if not registered_font:
    print("警告: 未找到中文字体文件，将使用系统默认字体")

# 定义固定的User-Agent
FIXED_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

KV = '''
#:import Clock kivy.clock.Clock

<PriceCard>:
    orientation: 'vertical'
    size_hint: None, None
    size: "280dp", "120dp"
    padding: "10dp"
    spacing: "5dp"
    md_bg_color: root.alert_color if root.is_alert else ((0.95, 0.6, 0.1, 1) if root.is_selected else (0.2, 0.2, 0.2, 1))
    
    MDLabel:
        text: root.symbol
        theme_text_color: "Custom"
        text_color: "white" if root.is_selected or root.is_alert else app.theme_cls.primary_color
        font_style: "H6"
        bold: True
        font_name: 'ChineseFont' if app.font_available else None
        
    MDLabel:
        text: root.price
        theme_text_color: "Custom" 
        text_color: "white" if root.is_selected or root.is_alert else app.theme_cls.primary_color
        font_style: "H4"
        bold: True
        font_name: 'ChineseFont' if app.font_available else None
        
    MDLabel:
        text: root.trend
        theme_text_color: "Custom"
        text_color: "white" if root.is_selected or root.is_alert else ((0, 0.7, 0, 1) if "上涨" in root.trend else (0.9, 0, 0, 1) if "下跌" in root.trend else (0.5, 0.5, 0.5, 1))
        font_style: "Caption"
        font_name: 'ChineseFont' if app.font_available else None

<AlertItem>:
    size_hint_y: None
    height: "60dp"
    padding: "10dp"
    
    MDBoxLayout:
        orientation: 'horizontal'
        spacing: "10dp"
        
        MDLabel:
            id: alert_text
            text: root.alert_text
            theme_text_color: "Custom"
            text_color: (0.9, 0, 0, 1) if root.triggered else app.theme_cls.primary_color
            font_name: 'ChineseFont' if app.font_available else None
            size_hint_x: 0.7
            halign: "left"
            valign: "center"
            
        MDBoxLayout:
            orientation: 'horizontal'
            size_hint_x: 0.3
            spacing: "5dp"
            
            MDFloatingActionButton:
                icon: "pencil"
                size_hint: None, None
                size: "40dp", "40dp"
                on_release: app.edit_alert(root)
                md_bg_color: app.theme_cls.primary_color
                
            MDFloatingActionButton:
                icon: "delete"
                size_hint: None, None
                size: "40dp", "40dp"
                on_release: app.delete_alert(root)
                md_bg_color: (0.9, 0, 0, 1)

MDScreen:
    md_bg_color: (0.1, 0.1, 0.1, 1)
    
    MDBoxLayout:
        orientation: 'vertical'
        spacing: "10dp"
        padding: "10dp"

        MDBoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: "56dp"
            spacing: "10dp"
            
            MDLabel:
                text: "黄金监控"
                font_style: "H4"
                halign: "center"
                size_hint_x: 0.6
                font_name: 'ChineseFont' if app.font_available else None
                
            MDFloatingActionButton:
                id: sound_btn
                icon: "volume-high"
                size_hint_x: 0.2
                on_release: app.toggle_sound_mode()
                md_bg_color: app.theme_cls.primary_color
                
            MDFloatingActionButton:
                icon: "refresh"
                size_hint_x: 0.2
                on_release: app.manual_refresh()
                md_bg_color: app.theme_cls.primary_color

        ScrollView:
            do_scroll_x: False
            
            MDGridLayout:
                id: price_grid
                cols: 2
                spacing: "10dp"
                size_hint_y: None
                height: self.minimum_height
                padding: "10dp"

        MDBoxLayout:
            orientation: 'vertical'
            size_hint_y: None
            height: "240dp"
            spacing: "5dp"
            
            MDLabel:
                text: "价格警报"
                font_style: "H6"
                size_hint_y: None
                height: "30dp"
                font_name: 'ChineseFont' if app.font_available else None
                
            MDBoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: "40dp"
                spacing: "5dp"
                
                MDTextField:
                    id: alert_symbol
                    hint_text: "Select Symbol"
                    size_hint_x: 0.4
                    text: ""
                    font_name: 'ChineseFont' if app.font_available else None
                    readonly: True
                    on_focus: if self.focus: app.show_symbol_menu(self)
                    
                MDTextField:
                    id: alert_condition
                    hint_text: "Condition"
                    size_hint_x: 0.2
                    text: ">="
                    readonly: True
                    on_focus: if self.focus: app.show_condition_menu(self)
                    
                MDTextField:
                    id: alert_price
                    hint_text: "Target Price"
                    size_hint_x: 0.3
                    input_filter: 'float'
                    
                MDFloatingActionButton:
                    icon: "plus"
                    size_hint_x: 0.1
                    on_release: app.add_alert()

            ScrollView:
                do_scroll_x: False
                
                MDList:
                    id: alert_list
                    size_hint_y: None
                    height: self.minimum_height

        MDBoxLayout:
            orientation: 'horizontal'
            size_hint_y: None
            height: "60dp"
            spacing: "10dp"
            
            MDRaisedButton:
                id: monitor_btn
                text: "开始监控"
                on_release: app.toggle_monitoring()
                size_hint_x: 0.6
                font_name: 'ChineseFont' if app.font_available else None
                
            MDLabel:
                id: status_label
                text: "就绪"
                halign: "center"
                theme_text_color: "Secondary"
                font_name: 'ChineseFont' if app.font_available else None

    MDNavigationDrawer:
        id: nav_drawer
        radius: (0, 16, 16, 0)

        MDBoxLayout:
            orientation: "vertical"
            spacing: "10dp"
            padding: "10dp"
            size_hint_y: None
            height: "250dp"

            MDLabel:
                text: "设置"
                font_style: "H5"
                size_hint_y: None
                height: self.texture_size[1]
                font_name: 'ChineseFont' if app.font_available else None

            MDBoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: "48dp"
                
                MDLabel:
                    text: "检查频率:"
                    size_hint_x: 0.6
                    font_name: 'ChineseFont' if app.font_available else None
                    
                MDTextField:
                    id: interval_input
                    text: "30"
                    size_hint_x: 0.4
                    input_filter: 'int'
                    font_name: 'ChineseFont' if app.font_available else None

            MDBoxLayout:
                orientation: 'horizontal'
                size_hint_y: None
                height: "48dp"
                
                MDLabel:
                    text: "警报模式:"
                    size_hint_x: 0.6
                    font_name: 'ChineseFont' if app.font_available else None
                    
                MDLabel:
                    id: sound_mode_label
                    text: "声音"
                    size_hint_x: 0.4
                    font_name: 'ChineseFont' if app.font_available else None

            MDRaisedButton:
                text: "保存设置"
                on_release: app.save_settings()
                font_name: 'ChineseFont' if app.font_available else None
'''

class PriceCard(MDCard):
    symbol = StringProperty("")
    price = StringProperty("0.00")
    trend = StringProperty("")
    is_selected = BooleanProperty(False)
    is_alert = BooleanProperty(False)  # 是否触发警报
    alert_color = (0.9, 0, 0, 1)  # 警报颜色
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.animation = None
        self.alert_state = False  # 当前警报状态
    
    def on_touch_down(self, touch):
        """点击卡片时自动填充到监控名称"""
        if self.collide_point(*touch.pos):
            app = MDApp.get_running_app()
            app.select_symbol(self.symbol)
        return super().on_touch_down(touch)
    
    def start_alert_animation(self):
        """开始警报闪烁动画"""
        print(f"开始闪烁动画: {self.symbol}")
        if self.animation:
            self.animation.stop(self)
        
        # 创建闪烁动画
        self.animation = Animation(md_bg_color=(0.9, 0, 0, 1), duration=0.8) + \
                        Animation(md_bg_color=(0.5, 0, 0, 1), duration=0.8)
        self.animation.repeat = True
        self.is_alert = True
        self.animation.start(self)
    
    def stop_alert_animation(self):
        """停止警报动画"""
        print(f"停止闪烁动画: {self.symbol}")
        if self.animation:
            self.animation.stop(self)
        self.is_alert = False
        self.md_bg_color = (0.2, 0.2, 0.2, 1)

class AlertItem(MDBoxLayout):
    symbol = StringProperty("")
    condition = StringProperty(">=")
    target_price = NumericProperty(0)
    triggered = BooleanProperty(False)
    alert_text = StringProperty("")
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = 'horizontal'
        self.update_text()
    
    def on_symbol(self, instance, value):
        self.update_text()
    
    def on_condition(self, instance, value):
        self.update_text()
    
    def on_target_price(self, instance, value):
        self.update_text()
    
    def update_text(self):
        # 使用中文条件符号
        condition_text = {
            ">=": "≥",
            "<=": "≤", 
            ">": ">",
            "<": "<"
        }.get(self.condition, self.condition)
        
        self.alert_text = f"{self.symbol} {condition_text} {self.target_price:.2f}"

class GoldMonitorApp(MDApp):
    font_available = BooleanProperty(registered_font)
    
    def __init__(self):
        super().__init__()
        self.monitoring = False
        self.check_interval = 30
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': FIXED_USER_AGENT})
        
        # 警报模式：0=声音, 1=震动, 2=静音
        self.sound_mode = 0
        self.sound_modes = ["声音", "震动", "静音"]
        self.sound_icons = ["volume-high", "vibrate", "volume-off"]
        
        # 存储真实价格数据
        self.real_prices = {
            "伦敦金": "获取中...",
            "人民币金价": "获取中...",
            "纽约黄金": "获取中...",
            "黄金期货": "获取中..."
        }
        
        self.alerts = []
        self.price_cards = {}
        self.last_update_time = "未更新"
        self.symbol_menu = None
        self.condition_menu = None
        self.edit_dialog = None
        self.current_edit_alert = None
        
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Amber"
        return Builder.load_string(KV)
    
    def on_start(self):
        """应用启动时调用"""
        self.load_settings()
        self.setup_price_cards()
        self.update_sound_display()
        self.refresh_prices()
        
        # 每60秒自动刷新
        Clock.schedule_interval(lambda dt: self.refresh_prices(), 60)
    
    def setup_price_cards(self):
        """设置价格卡片"""
        price_grid = self.root.ids.price_grid
        price_grid.clear_widgets()
        self.price_cards = {}
        
        symbols = ["伦敦金", "人民币金价", "纽约黄金", "黄金期货"]
        for symbol in symbols:
            card = PriceCard(symbol=symbol)
            self.price_cards[symbol] = card
            price_grid.add_widget(card)
    
    def toggle_sound_mode(self):
        """切换声音模式"""
        self.sound_mode = (self.sound_mode + 1) % 3
        self.update_sound_display()
        self.root.ids.status_label.text = f"警报模式: {self.sound_modes[self.sound_mode]}"
    
    def update_sound_display(self):
        """更新声音模式显示"""
        sound_btn = self.root.ids.sound_btn
        sound_btn.icon = self.sound_icons[self.sound_mode]
        self.root.ids.sound_mode_label.text = self.sound_modes[self.sound_mode]
    
    def trigger_alert_notification(self, symbol):
        """触发警报通知"""
        print(f"触发警报通知: {symbol}, 模式: {self.sound_modes[self.sound_mode]}")
        
        if self.sound_mode == 0:  # 声音模式
            # 在Android上播放声音
            try:
                from jnius import autoclass
                MediaPlayer = autoclass('android.media.MediaPlayer')
                player = MediaPlayer()
                # 这里可以设置警报声音
                player.start()
                print("播放警报声音")
            except:
                # 在PC上使用系统声音或忽略
                print(f"PC端声音警报: {symbol}")
                
        elif self.sound_mode == 1:  # 震动模式
            # 在Android上触发震动
            try:
                from jnius import autoclass
                Context = autoclass('android.content.Context')
                vibrator_service = autoclass('android.os.Vibrator')
                vibrator = vibrator_service()
                # 震动1秒
                vibrator.vibrate(1000)
                print("触发震动")
            except:
                print(f"PC端震动警报: {symbol}")
                
        else:  # 静音模式
            print(f"静音警报: {symbol}")
    
    def select_symbol(self, symbol):
        """选择品种"""
        self.root.ids.alert_symbol.text = symbol
    
    def show_symbol_menu(self, text_field):
        """显示品种选择菜单 - 使用英文避免乱码"""
        menu_items = [
            {
                "text": "London Gold",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="伦敦金": self.select_symbol_and_close(x),
            },
            {
                "text": "CNY Gold Price", 
                "viewclass": "OneLineListItem",
                "on_release": lambda x="人民币金价": self.select_symbol_and_close(x),
            },
            {
                "text": "NY Gold",
                "viewclass": "OneLineListItem", 
                "on_release": lambda x="纽约黄金": self.select_symbol_and_close(x),
            },
            {
                "text": "Gold Futures",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="黄金期货": self.select_symbol_and_close(x),
            },
        ]
        self.symbol_menu = MDDropdownMenu(
            caller=text_field,
            items=menu_items,
            width_mult=4,
        )
        self.symbol_menu.open()
    
    def select_symbol_and_close(self, symbol):
        """选择品种并关闭菜单"""
        self.select_symbol(symbol)
        if self.symbol_menu:
            self.symbol_menu.dismiss()
    
    def show_condition_menu(self, text_field):
        """显示条件选择菜单"""
        menu_items = [
            {
                "text": "Greater or Equal >=",
                "viewclass": "OneLineListItem",
                "on_release": lambda x=">=": self.select_condition_and_close(x),
            },
            {
                "text": "Less or Equal <=", 
                "viewclass": "OneLineListItem",
                "on_release": lambda x="<=": self.select_condition_and_close(x),
            },
            {
                "text": "Greater >",
                "viewclass": "OneLineListItem", 
                "on_release": lambda x=">": self.select_condition_and_close(x),
            },
            {
                "text": "Less <",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="<": self.select_condition_and_close(x),
            },
        ]
        self.condition_menu = MDDropdownMenu(
            caller=text_field,
            items=menu_items,
            width_mult=4,
        )
        self.condition_menu.open()
    
    def select_condition_and_close(self, condition):
        """选择条件并关闭菜单"""
        self.root.ids.alert_condition.text = condition
        if self.condition_menu:
            self.condition_menu.dismiss()
    
    def manual_refresh(self):
        """手动刷新行情"""
        self.root.ids.status_label.text = "刷新中..."
        self.refresh_prices()
    
    @retry(stop_max_attempt_number=2, wait_fixed=2000)
    def get_real_gold_price(self):
        """获取真实黄金价格 - 多个数据源"""
        price_sources = []
        
        # 数据源1: goldprice.org (主要数据源)
        try:
            url = 'https://data-asg.goldprice.org/dbXRates/USD'
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'items' in data and data['items']:
                gold_data = data['items'][0]
                usd_per_ounce = gold_data['xauPrice']
                
                # 转换为人民币
                cny_per_gram = (usd_per_ounce * 7.2) / 31.1035
                
                # 计算涨跌幅 - 使用正确的字段
                change = gold_data.get('pcXau', 0)  # 百分比变化
                change_amount = gold_data.get('chXau', 0)  # 金额变化
                
                trend_text = ""
                if change_amount > 0:
                    trend_text = f"上涨 +{change_amount:.2f} USD"
                elif change_amount < 0:
                    trend_text = f"下跌 {change_amount:.2f} USD"
                else:
                    trend_text = "持平"
                
                price_sources.append({
                    "伦敦金": round(usd_per_ounce, 2),
                    "人民币金价": round(cny_per_gram, 2),
                    "涨跌幅": f"{change}%",
                    "趋势": trend_text
                })
                print(f"数据源1获取成功: 伦敦金 {usd_per_ounce} USD")
        except Exception as e:
            print(f"数据源1获取失败: {e}")
        
        # 如果没有获取到数据，返回None
        if not price_sources:
            return None
        
        # 合并数据源，优先使用第一个成功的数据源
        merged_data = price_sources[0]
        
        return merged_data
    
    def refresh_prices(self, *args):
        """刷新价格显示 - 只使用真实数据"""
        try:
            self.root.ids.status_label.text = "获取数据中..."
            
            # 获取真实价格数据
            real_data = self.get_real_gold_price()
            
            if real_data:
                # 更新价格显示
                for symbol, card in self.price_cards.items():
                    if symbol in real_data:
                        price = real_data[symbol]
                        card.price = f"{price}"
                        
                        # 显示趋势信息
                        if "趋势" in real_data:
                            trend = real_data["趋势"]
                            if "上涨" in trend:
                                card.trend = f"🟢 {trend}"
                            elif "下跌" in trend:
                                card.trend = f"🔴 {trend}"
                            else:
                                card.trend = f"➡️ {trend}"
                        elif "涨跌幅" in real_data:
                            card.trend = real_data["涨跌幅"]
                        else:
                            card.trend = "实时数据"
                    else:
                        card.price = "暂无数据"
                        card.trend = "等待刷新"
                
                # 检查警报
                self.check_alerts(real_data)
                
                # 更新状态
                self.last_update_time = datetime.now().strftime("%H:%M:%S")
                self.root.ids.status_label.text = f"已更新 {self.last_update_time}"
                
            else:
                # 没有获取到数据
                for card in self.price_cards.values():
                    card.price = "获取失败"
                    card.trend = "点击刷新"
                
                self.root.ids.status_label.text = "数据获取失败，请检查网络"
            
        except Exception as e:
            print(f"刷新价格错误: {e}")
            self.root.ids.status_label.text = "刷新失败"
            
            # 显示错误状态
            for card in self.price_cards.values():
                card.price = "错误"
                card.trend = "刷新重试"
    
    def add_alert(self):
        """添加警报"""
        try:
            symbol = self.root.ids.alert_symbol.text.strip()
            condition = self.root.ids.alert_condition.text.strip()
            price_text = self.root.ids.alert_price.text.strip()
            
            print(f"添加警报: symbol={symbol}, condition={condition}, price={price_text}")
            
            if not symbol or not price_text:
                print("警报信息不完整")
                self.root.ids.status_label.text = "请填写完整信息"
                return
                
            target_price = float(price_text)
            
            # 创建警报项
            item = AlertItem()
            item.symbol = symbol
            item.condition = condition
            item.target_price = target_price
            
            # 添加到界面
            self.root.ids.alert_list.add_widget(item)
            
            # 保存到警报列表
            alert = {
                'symbol': symbol,
                'condition': condition,
                'target_price': target_price,
                'triggered': False,
                'item': item
            }
            self.alerts.append(alert)
            
            # 清空输入框
            self.root.ids.alert_price.text = ""
            
            # 更新列表高度
            self.update_alert_list_height()
            
            print(f"警报添加成功，当前警报数量: {len(self.alerts)}")
            self.root.ids.status_label.text = "警报添加成功"
            
        except ValueError as e:
            print(f"价格格式错误: {e}")
            self.root.ids.status_label.text = "价格格式错误"
        except Exception as e:
            print(f"添加警报时发生错误: {e}")
            print(traceback.format_exc())
            self.root.ids.status_label.text = "添加警报失败"
    
    def update_alert_list_height(self):
        """更新警报列表高度"""
        alert_list = self.root.ids.alert_list
        alert_list.height = len(alert_list.children) * 70  # 每个项目70dp高度
    
    def edit_alert(self, alert_item):
        """编辑警报"""
        try:
            self.current_edit_alert = alert_item
            
            # 找到对应的警报数据
            alert_data = None
            for alert in self.alerts:
                if alert['item'] == alert_item:
                    alert_data = alert
                    break
            
            if alert_data:
                # 创建编辑对话框
                content = MDBoxLayout(
                    orientation="vertical",
                    spacing="10dp",
                    size_hint_y=None,
                    height="120dp"
                )
                
                # 添加条件选择
                condition_field = MDTextField(
                    hint_text="Condition",
                    text=alert_data['condition'],
                    readonly=True
                )
                condition_field.bind(on_focus=lambda x, y: self.show_edit_condition_menu(condition_field))
                
                # 添加价格输入
                price_field = MDTextField(
                    hint_text="Target Price", 
                    text=str(alert_data['target_price']),
                    input_filter='float'
                )
                
                content.add_widget(condition_field)
                content.add_widget(price_field)
                
                self.edit_dialog = MDDialog(
                    title="Edit Alert",
                    type="custom",
                    content_cls=content,
                    buttons=[
                        MDFlatButton(
                            text="CANCEL",
                            on_release=lambda x: self.edit_dialog.dismiss()
                        ),
                        MDFlatButton(
                            text="SAVE", 
                            on_release=self.save_edited_alert
                        ),
                    ],
                )
                
                self.edit_dialog.condition_field = condition_field
                self.edit_dialog.price_field = price_field
                self.edit_dialog.open()
                
        except Exception as e:
            print(f"编辑警报错误: {e}")
            self.root.ids.status_label.text = "Edit failed"
    
    def show_edit_condition_menu(self, text_field):
        """显示编辑时的条件菜单"""
        menu_items = [
            {
                "text": "Greater or Equal >=",
                "viewclass": "OneLineListItem",
                "on_release": lambda x=">=": self.select_edit_condition_and_close(x, text_field),
            },
            {
                "text": "Less or Equal <=", 
                "viewclass": "OneLineListItem",
                "on_release": lambda x="<=": self.select_edit_condition_and_close(x, text_field),
            },
            {
                "text": "Greater >",
                "viewclass": "OneLineListItem", 
                "on_release": lambda x=">": self.select_edit_condition_and_close(x, text_field),
            },
            {
                "text": "Less <",
                "viewclass": "OneLineListItem",
                "on_release": lambda x="<": self.select_edit_condition_and_close(x, text_field),
            },
        ]
        condition_menu = MDDropdownMenu(
            caller=text_field,
            items=menu_items,
            width_mult=4,
        )
        condition_menu.open()
    
    def select_edit_condition_and_close(self, condition, text_field):
        """选择编辑条件并关闭菜单"""
        text_field.text = condition
        # 这里不需要保存到对话框，因为text_field已经绑定了
    
    def save_edited_alert(self, instance):
        """保存编辑的警报"""
        try:
            if not self.current_edit_alert:
                return
            
            new_condition = self.edit_dialog.condition_field.text
            new_price = float(self.edit_dialog.price_field.text)
            
            # 更新警报项
            self.current_edit_alert.condition = new_condition
            self.current_edit_alert.target_price = new_price
            self.current_edit_alert.update_text()
            
            # 更新警报数据
            for alert in self.alerts:
                if alert['item'] == self.current_edit_alert:
                    alert['condition'] = new_condition
                    alert['target_price'] = new_price
                    alert['triggered'] = False  # 重置触发状态
                    self.current_edit_alert.triggered = False
                    break
            
            self.edit_dialog.dismiss()
            self.root.ids.status_label.text = "Alert updated"
            
        except ValueError:
            self.root.ids.status_label.text = "Price format error"
        except Exception as e:
            print(f"保存编辑警报错误: {e}")
            self.root.ids.status_label.text = "Update failed"
    
    def delete_alert(self, alert_item):
        """删除警报"""
        try:
            # 从界面移除
            self.root.ids.alert_list.remove_widget(alert_item)
            
            # 从数据列表移除
            self.alerts = [alert for alert in self.alerts if alert['item'] != alert_item]
            
            # 更新列表高度
            self.update_alert_list_height()
            
            self.root.ids.status_label.text = "Alert deleted"
            print(f"警报删除成功，当前警报数量: {len(self.alerts)}")
        except Exception as e:
            print(f"删除警报错误: {e}")
            self.root.ids.status_label.text = "Delete failed"
    
    def check_alerts(self, prices):
        """检查警报"""
        try:
            # 先停止所有警报动画
            for card in self.price_cards.values():
                card.stop_alert_animation()
            
            any_alert_triggered = False
            
            for alert in self.alerts:
                if not alert['triggered']:
                    current_price = prices.get(alert['symbol'])
                    if current_price:
                        # 根据条件检查警报
                        condition_met = False
                        if alert['condition'] == ">=" and current_price >= alert['target_price']:
                            condition_met = True
                        elif alert['condition'] == "<=" and current_price <= alert['target_price']:
                            condition_met = True
                        elif alert['condition'] == ">" and current_price > alert['target_price']:
                            condition_met = True
                        elif alert['condition'] == "<" and current_price < alert['target_price']:
                            condition_met = True
                        
                        if condition_met:
                            print(f"警报触发: {alert['symbol']} {alert['condition']} {alert['target_price']}, 当前价格: {current_price}")
                            alert['triggered'] = True
                            alert['item'].triggered = True
                            
                            # 触发对应卡片的闪烁动画
                            if alert['symbol'] in self.price_cards:
                                card = self.price_cards[alert['symbol']]
                                card.start_alert_animation()
                                any_alert_triggered = True
                            
                            # 触发警报通知
                            self.trigger_alert_notification(alert['symbol'])
            
            if any_alert_triggered:
                self.root.ids.status_label.text = "Alert Triggered!"
                print("有警报触发！")
                
        except Exception as e:
            print(f"检查警报错误: {e}")
    
    def toggle_monitoring(self):
        """切换监控状态"""
        try:
            self.monitoring = not self.monitoring
            btn = self.root.ids.monitor_btn
            
            if self.monitoring:
                btn.text = "停止监控"
                btn.md_bg_color = (0.9, 0, 0, 1)  # 红色
                self.root.ids.status_label.text = "监控中..."
            else:
                btn.text = "开始监控" 
                btn.md_bg_color = self.theme_cls.primary_color
                self.root.ids.status_label.text = "已停止"
        except Exception as e:
            print(f"切换监控状态错误: {e}")
    
    def nav_drawer_set_state(self):
        """打开/关闭导航菜单"""
        try:
            nav = self.root.ids.nav_drawer
            nav.set_state("toggle")
        except Exception as e:
            print(f"导航菜单错误: {e}")
    
    def show_settings(self):
        """显示设置"""
        self.nav_drawer_set_state()
    
    def save_settings(self):
        """保存设置"""
        try:
            interval = self.root.ids.interval_input.text
            self.check_interval = int(interval)
            self.root.ids.status_label.text = "设置已保存"
        except:
            self.root.ids.status_label.text = "设置保存失败"
    
    def load_settings(self):
        """加载设置"""
        # 这里可以添加从文件加载设置的逻辑
        pass

if __name__ == '__main__':
    try:
        GoldMonitorApp().run()
    except Exception as e:
        print(f"应用程序崩溃: {e}")
        print(traceback.format_exc())
        input("按回车键退出...")