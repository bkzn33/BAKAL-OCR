from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button

class TestApp(App):
    def build(self):
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='Kivy is working!', font_size='24sp'))
        layout.add_widget(Button(text='Click me', font_size='18sp'))
        return layout

if __name__ == '__main__':
    TestApp().run()