# main.py
# Entry point for the Kivy application.

import kivy
kivy.require("2.1.0") # Specify Kivy version (optional, but good practice)

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.popup import Popup
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.config import ConfigParser
from kivy.clock import Clock
from kivy.factory import Factory # For dynamically creating widgets
from kivy.utils import platform as kivy_platform # For platform-specific actions like opening links
import webbrowser # For opening links

# Import backend logic
from backend_logic import (
    initialize_backend, shutdown_backend, remove_html_tags, 
    feed_names, feed_urls, get_feed_articles, # For feeds and articles
    generate_summary_async, # For generating summaries
    post_to_linkedin_async, # For posting
    schedule_linkedin_post, cancel_scheduled_post, # For scheduling
    update_linkedin_credentials, get_linkedin_profile_info, # For settings
    load_last_check_dates, save_last_check_dates, # For app config
    load_schedules, save_schedules, # For app config
    initialize_ai_clients, # For app config
    AZURE_TOKEN, GITHUB_TOKEN, ACCESS_TOKEN, LINKEDIN_REFRESH_TOKEN, 
    LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET # To update them
)

import asyncio
import os
import json # For settings panel data
from datetime import datetime

# Load the KV file for the GUI
Builder.load_file("app_gui.kv")

class MainScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app:
            self.ids.status_label.text = f"Bem-vindo! Feeds: {len(feed_names)}"

    def test_button_action(self):
        app = App.get_running_app()
        if app:
            app.test_backend_functionality(self.ids.main_content_label)

class SettingsScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app:
            self.ids.azure_token_input.text = app.config.getdefault("Credentials", "azure_token", "")
            self.ids.linkedin_client_id_input.text = app.config.getdefault("Credentials", "linkedin_client_id", "")
            self.ids.linkedin_client_secret_input.text = app.config.getdefault("Credentials", "linkedin_client_secret", "")
            self.ids.linkedin_access_token_input.text = app.config.getdefault("Credentials", "linkedin_access_token", "")
            self.ids.linkedin_refresh_token_input.text = app.config.getdefault("Credentials", "linkedin_refresh_token", "")

class FeedScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app:
            app.populate_feed_list_ui(self.ids.feed_list_layout)

class ArticleListScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app and self.selected_feed_command:
            self.ids.article_screen_title.text = f"Artigos de: {self.selected_feed_name}"
            app.load_articles_for_feed(self.selected_feed_command, self.selected_feed_name, self.ids.article_list_layout)
        else:
            self.ids.article_screen_title.text = "Nenhum feed selecionado"
            self.ids.article_list_layout.clear_widgets()
            self.ids.article_list_layout.add_widget(Label(text="Por favor, selecione um feed primeiro."))

class ArticleDetailScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app and self.article_data:
            self.ids.detail_title_label.text = self.article_data.get("feed_name", "Detalhes do Artigo")
            self.ids.detail_translated_title.text = f"Título Traduzido: {self.article_data.get("translated_title", "N/A")}"
            self.ids.detail_original_title.text = f"Título Original: {self.article_data.get("original_title", "N/A")}"
            link = self.article_data.get("link", "N/A")
            self.ids.detail_link.text = f"Link: [ref={link}]{link}[/ref]"
            self.ids.detail_published_date.text = f"Publicado em: {self.article_data.get("published_date", "N/A")}"
            self.ids.detail_cleaned_summary.text = self.article_data.get("cleaned_summary", "Nenhum resumo disponível.")
            # Reset and hide generated summary TextInput
            self.ids.generated_summary_label.opacity = 0
            self.ids.generated_summary_text_input.height = "0dp"
            self.ids.generated_summary_text_input.opacity = 0
            self.ids.generated_summary_text_input.text = ""
            self.ids.post_linkedin_button.disabled = True
            self.ids.generate_summary_button.disabled = False
        else:
            self.ids.detail_title_label.text = "Erro: Artigo não carregado"

class ScheduleScreen(Screen):
    def on_enter(self, *args):
        app = App.get_running_app()
        if app:
            app.populate_schedule_list_ui(self.ids.schedule_list_layout)

class LinkedinAutopostApp(App):
    new_schedule_popup = None # To hold the popup instance

    def build(self):
        self.title = "LinkedIn AutoPost App"
        Clock.schedule_once(self.async_initialize_backend, 0)
        return Builder.load_file("app_gui.kv")

    def async_initialize_backend(self, dt=None):
        async def run_init():
            await initialize_backend()
            self.load_credentials_from_kivy_config_to_backend()
            kivy_config_dict = {s: dict(self.config.items(s)) for s in self.config.sections()}
            await asyncio.to_thread(initialize_ai_clients, kivy_config_dict.get("Credentials", {}))
            from backend_logic import restore_saved_schedules_from_file, initialize_text_analytics_client
            text_analytics_creds = {
                "azure_text_analytics_endpoint": self.config.getdefault("Credentials", "azure_text_analytics_endpoint", None),
                "azure_text_analytics_key": self.config.getdefault("Credentials", "azure_text_analytics_key", None)
            }
            await asyncio.to_thread(initialize_text_analytics_client, text_analytics_creds)
            await restore_saved_schedules_from_file(self.update_main_status_label)
            self.update_main_status_label("Backend inicializado.")
        asyncio.ensure_future(run_init())

    def build_config(self, config):
        config.setdefaults("Credentials", {
            "azure_token": "", "github_token": "",
            "linkedin_client_id": "", "linkedin_client_secret": "",
            "linkedin_access_token": "", "linkedin_refresh_token": "",
            "azure_text_analytics_endpoint": "", "azure_text_analytics_key": ""
        })
        config.setdefaults("General", {"user_name": "Usuário"})
        config.setdefaults("AISettings", {"default_model": "gpt-4o"})

    def load_credentials_from_kivy_config_to_backend(self):
        import backend_logic as bl
        bl.AZURE_TOKEN = self.config.getdefault("Credentials", "azure_token", bl.AZURE_TOKEN)
        bl.GITHUB_TOKEN = self.config.getdefault("Credentials", "github_token", bl.AZURE_TOKEN)
        bl.ACCESS_TOKEN = self.config.getdefault("Credentials", "linkedin_access_token", bl.ACCESS_TOKEN)
        bl.LINKEDIN_REFRESH_TOKEN = self.config.getdefault("Credentials", "linkedin_refresh_token", bl.LINKEDIN_REFRESH_TOKEN)
        bl.LINKEDIN_CLIENT_ID = self.config.getdefault("Credentials", "linkedin_client_id", bl.LINKEDIN_CLIENT_ID)
        bl.LINKEDIN_CLIENT_SECRET = self.config.getdefault("Credentials", "linkedin_client_secret", bl.LINKEDIN_CLIENT_SECRET)
        bl.AZURE_TEXT_ANALYTICS_ENDPOINT = self.config.getdefault("Credentials", "azure_text_analytics_endpoint", bl.AZURE_TEXT_ANALYTICS_ENDPOINT)
        bl.AZURE_TEXT_ANALYTICS_KEY = self.config.getdefault("Credentials", "azure_text_analytics_key", bl.AZURE_TEXT_ANALYTICS_KEY)
        print("Credenciais Kivy Config -> Backend.")
        kivy_config_dict = {s: dict(self.config.items(s)) for s in self.config.sections()}
        asyncio.ensure_future(asyncio.to_thread(initialize_ai_clients, kivy_config_dict.get("Credentials", {})))
        text_analytics_creds = {
            "azure_text_analytics_endpoint": bl.AZURE_TEXT_ANALYTICS_ENDPOINT,
            "azure_text_analytics_key": bl.AZURE_TEXT_ANALYTICS_KEY
        }
        from backend_logic import initialize_text_analytics_client
        asyncio.ensure_future(asyncio.to_thread(initialize_text_analytics_client, text_analytics_creds))

    def save_settings(self, azure_token, linkedin_client_id, linkedin_client_secret, linkedin_access_token, linkedin_refresh_token):
        self.config.set("Credentials", "azure_token", azure_token)
        self.config.set("Credentials", "github_token", azure_token)
        self.config.set("Credentials", "linkedin_client_id", linkedin_client_id)
        self.config.set("Credentials", "linkedin_client_secret", linkedin_client_secret)
        self.config.set("Credentials", "linkedin_access_token", linkedin_access_token)
        self.config.set("Credentials", "linkedin_refresh_token", linkedin_refresh_token)
        self.config.write()
        self.update_main_status_label("Configurações de API salvas!")
        self.load_credentials_from_kivy_config_to_backend()
        if linkedin_refresh_token and linkedin_client_id and linkedin_client_secret:
            self.update_main_status_label("Verificando LinkedIn...")
            asyncio.ensure_future(get_linkedin_profile_info(self.update_main_status_label))

    def populate_feed_list_ui(self, feed_list_layout):
        feed_list_layout.clear_widgets()
        if not feed_names:
            feed_list_layout.add_widget(Label(text="Nenhum feed configurado."))
            return
        for name, command in sorted(feed_names.items()):
            btn = Factory.ListItemButton(text=name)
            btn.bind(on_press=lambda instance, cmd=command, fname=name: self.on_feed_selected(cmd, fname))
            feed_list_layout.add_widget(btn)

    def on_feed_selected(self, feed_command, feed_name):
        article_list_screen = self.root.get_screen("articles")
        article_list_screen.selected_feed_command = feed_command
        article_list_screen.selected_feed_name = feed_name
        self.root.current = "articles"

    def load_articles_for_feed(self, feed_command, feed_name, article_layout, force_refresh=False):
        article_layout.clear_widgets()
        loading_label = Label(text=f"Carregando artigos de {feed_name}...")
        article_layout.add_widget(loading_label)
        async def fetch_and_display():
            def update_progress(message, level="info"):
                Clock.schedule_once(lambda dt: setattr(loading_label, "text", message))
            articles = await get_feed_articles(feed_command, ui_callback=update_progress)
            Clock.schedule_once(lambda dt: article_layout.clear_widgets())
            if not articles:
                Clock.schedule_once(lambda dt: article_layout.add_widget(Label(text=f"Nenhum artigo para {feed_name}.")))
                return
            for article_data_item in articles:
                article_text = f"{article_data_item["translated_title"]}\n< {article_data_item["published_date"]} >"
                item_btn = Factory.ListItemButton(text=article_text)
                item_btn.bind(on_press=lambda instance, art=article_data_item: self.on_article_selected(art))
                Clock.schedule_once(lambda dt, btn=item_btn: article_layout.add_widget(btn))
        asyncio.ensure_future(fetch_and_display())

    def on_article_selected(self, article_data):
        detail_screen = self.root.get_screen("article_detail")
        detail_screen.article_data = article_data
        self.root.current = "article_detail"

    def generate_summary_for_article(self, article_data):
        if not article_data:
            self.update_main_status_label("Erro: Nenhum dado de artigo para gerar resumo.", "error")
            return
        detail_screen = self.root.get_screen("article_detail")
        detail_screen.ids.generate_summary_button.disabled = True
        self.update_main_status_label(f"Gerando resumo para: {article_data.get("original_title", "")[:30]}...", "info")
        content_to_summarize = article_data.get("cleaned_summary", article_data.get("raw_summary", ""))
        if not content_to_summarize: content_to_summarize = article_data.get("original_title", "")
        article_url = article_data.get("link", "")
        preferred_model = self.config.getdefault("AISettings", "default_model", "gpt-4o")
        async def do_generate():
            summary_text = await generate_summary_async(content_to_summarize, article_url, preferred_model, self.update_main_status_label)
            def update_ui_summary(dt=None):
                detail_screen.ids.generated_summary_label.opacity = 1
                detail_screen.ids.generated_summary_text_input.height = "150dp" # Make TextInput visible and set height
                detail_screen.ids.generated_summary_text_input.opacity = 1
                detail_screen.ids.generated_summary_text_input.text = summary_text # Populate TextInput
                if not summary_text.startswith("Falha"):
                    detail_screen.ids.post_linkedin_button.disabled = False
                else:
                    detail_screen.ids.generate_summary_button.disabled = False
            Clock.schedule_once(update_ui_summary)
        asyncio.ensure_future(do_generate())

    def post_generated_summary_to_linkedin(self, article_data, summary_text_from_input):
        # summary_text_from_input is now directly from the TextInput in .kv
        if not article_data or not summary_text_from_input:
            self.update_main_status_label("Erro: Dados do artigo ou resumo (editado) ausentes.", "error")
            return
        self.update_main_status_label("Preparando para postar no LinkedIn...", "info")
        title = article_data.get("translated_title", article_data.get("original_title", "Artigo Interessante"))
        url = article_data.get("link", "")
        async def do_post():
            result = await post_to_linkedin_async(title, summary_text_from_input, url, self.update_main_status_label)
            if result.get("success"):
                self.update_main_status_label(f"Postado! ID: {result.get("id")}", "success")
            else:
                self.update_main_status_label(f"Falha: {result.get("error")}", "error")
        asyncio.ensure_future(do_post())

    def populate_schedule_list_ui(self, schedule_list_layout):
        schedule_list_layout.clear_widgets()
        schedules = load_schedules()
        if not schedules:
            schedule_list_layout.add_widget(Label(text="Nenhum agendamento encontrado."))
            return
        for job_id, job_data in sorted(schedules.items(), key=lambda item: item[1].get("scheduled_time_local", "")):
            item_layout = BoxLayout(orientation="horizontal", size_hint_y=None, height="48dp", spacing="10dp")
            info_text = f"{job_data.get("title", "N/A")[:40]}...\n@{job_data.get("scheduled_time_local", "N/A").split("T")[0]} {job_data.get("scheduled_time_local", "N/A").split("T")[1][:5] if "T" in job_data.get("scheduled_time_local", "") else ""}"
            info_label = Label(text=info_text, size_hint_x=0.8, text_size=(schedule_list_layout.width*0.7, None), halign="left")
            cancel_button = Button(text="Cancelar", size_hint_x=0.2)
            cancel_button.bind(on_press=lambda instance, j_id=job_id: self.on_cancel_schedule_pressed(j_id))
            item_layout.add_widget(info_label)
            item_layout.add_widget(cancel_button)
            schedule_list_layout.add_widget(item_layout)

    def on_cancel_schedule_pressed(self, job_id):
        self.update_main_status_label(f"Cancelando agendamento {job_id}...", "info")
        async def do_cancel():
            success, message = await cancel_scheduled_post(job_id, self.update_main_status_label)
            if success:
                self.update_main_status_label(message, "success")
                schedule_screen = self.root.get_screen("schedules")
                if schedule_screen:
                    self.populate_schedule_list_ui(schedule_screen.ids.schedule_list_layout)
            else:
                self.update_main_status_label(message, "error")
        asyncio.ensure_future(do_cancel())

    def open_new_schedule_popup(self):
        if self.new_schedule_popup and self.new_schedule_popup.open:
            self.new_schedule_popup.dismiss()
        content = GridLayout(cols=1, spacing="10dp", size_hint_y=None)
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(Label(text="Título do Post:"))
        title_input = TextInput(multiline=False, hint_text="Título para o LinkedIn")
        content.add_widget(title_input)
        content.add_widget(Label(text="Resumo/Conteúdo do Post:"))
        summary_input = TextInput(multiline=True, hint_text="Conteúdo a ser postado", size_hint_y=None, height="100dp")
        content.add_widget(summary_input)
        content.add_widget(Label(text="URL do Artigo (Opcional):"))
        url_input = TextInput(multiline=False, hint_text="https://exemplo.com/artigo")
        content.add_widget(url_input)
        content.add_widget(Label(text="Data do Agendamento (YYYY-MM-DD):"))
        date_input = TextInput(multiline=False, hint_text=datetime.now().strftime("%Y-%m-%d"))
        content.add_widget(date_input)
        content.add_widget(Label(text="Hora do Agendamento (HH:MM - 24h):"))
        time_input = TextInput(multiline=False, hint_text=datetime.now().strftime("%H:%M"))
        content.add_widget(time_input)
        button_layout = BoxLayout(size_hint_y=None, height="50dp", spacing="10dp")
        submit_button = Button(text="Agendar Post")
        cancel_button = Button(text="Cancelar Popup")
        button_layout.add_widget(submit_button)
        button_layout.add_widget(cancel_button)
        content.add_widget(button_layout)
        self.new_schedule_popup = Popup(title="Novo Agendamento LinkedIn", content=content, size_hint=(0.9, 0.8), auto_dismiss=False)
        def _submit_schedule(instance):
            scheduled_time_str = f"{date_input.text} {time_input.text}"
            self.update_main_status_label(f"Tentando agendar para {scheduled_time_str}...", "info")
            async def do_schedule():
                success, message_or_id = await schedule_linkedin_post(
                    self.update_main_status_label, 
                    title_input.text, 
                    summary_input.text, 
                    url_input.text, 
                    scheduled_time_str
                )
                if success:
                    self.update_main_status_label(f"Agendado! ID: {message_or_id}", "success")
                    self.new_schedule_popup.dismiss()
                    schedule_screen = self.root.get_screen("schedules")
                    if schedule_screen:
                        self.populate_schedule_list_ui(schedule_screen.ids.schedule_list_layout)
                else:
                    self.update_main_status_label(f"Falha ao agendar: {message_or_id}", "error")
            asyncio.ensure_future(do_schedule())
        submit_button.bind(on_press=_submit_schedule)
        cancel_button.bind(on_press=self.new_schedule_popup.dismiss)
        self.new_schedule_popup.open()

    def open_link(self, url):
        try:
            if kivy_platform == "android":
                from jnius import autoclass
                Intent = autoclass("android.content.Intent")
                Uri = autoclass("android.net.Uri")
                PythonActivity = autoclass("org.kivy.android.PythonActivity")
                currentActivity = PythonActivity.mActivity
                intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                currentActivity.startActivity(intent)
            else:
                webbrowser.open(url)
            self.update_main_status_label(f"Tentando abrir link: {url}", "info")
        except Exception as e:
            self.update_main_status_label(f"Erro ao abrir link: {e}", "error")
            print(f"Error opening link: {e}")

    def test_backend_functionality(self, output_label_widget):
        main_screen = self.root.get_screen("main_screen")
        target_label = main_screen.ids.main_content_label if main_screen else output_label_widget
        target_label.text = "Testando backend...\n"
        html_text = "<p>Olá Mundo Kivy!</p> <b>Este é um teste.</b>"
        cleaned = remove_html_tags(html_text)
        target_label.text += f"Limpeza HTML: {cleaned}\n"
        async def run_linkedin_check():
            target_label.text += "Verificando perfil LinkedIn...\n"
            await get_linkedin_profile_info(self.update_main_status_label)
        asyncio.ensure_future(run_linkedin_check())

    def update_main_status_label(self, message, level="info"):
        def update_ui(dt=None):
            if self.root and hasattr(self.root, "ids") and self.root.ids:
                main_screen = self.root.get_screen("main_screen")
                if main_screen and hasattr(main_screen, "ids") and main_screen.ids.get("status_label"):
                    main_screen.ids.status_label.text = f"[{level.upper()}] {message}"
            print(f"UI_{level.upper()}: {message}")
        Clock.schedule_once(update_ui)

    def on_stop(self):
        print("App parando, finalizando backend...")
        async def run_shutdown(): 
            await shutdown_backend()
            print("Backend finalizado.")
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(run_shutdown())
                import time; time.sleep(0.5)
            else:
                asyncio.run(run_shutdown())
        except Exception as e:
            print(f"Erro durante o shutdown do asyncio: {e}")
        print("Processo de parada do App concluído.")

if __name__ == "__main__":
    app = LinkedinAutopostApp()
    app.run()

