from PySide6.QtWidgets import QVBoxLayout, QLabel, QPushButton

from screens.base_screen import BaseScreen


class HomeScreen(BaseScreen):
    show_language_controls = True

    def __init__(self, ctx, router, parent=None):
        super().__init__(ctx=ctx, router=router, parent=parent)

        layout = QVBoxLayout(self)
        layout.setSpacing(16)

        self.title = QLabel("")
        self.title.setWordWrap(True)
        self.title.setStyleSheet("font-size: 20px; font-weight: 600;")
        layout.addWidget(self.title)
        self.title.setVisible(False)

        self.btn_start = QPushButton("")
        self.btn_start.clicked.connect(self._start)
        layout.addWidget(self.btn_start)

        layout.addStretch(1)
        self._apply_language_texts()

    def on_language_changed(self, language: str) -> None:
        self._apply_language_texts()

    def _apply_language_texts(self) -> None:
        fa = self.ctx.config.language == "fa"
        description = (
            "مینی کاگ ابزاری سریع (۳ دقیقه‌ای) و ساده برای غربالگری شناختی است که بیشتر برای بزرگسالان "
            "مسن استفاده می‌شود تا نشانه‌های اولیه زوال عقل یا اختلال شناختی را شناسایی کند. این آزمون ترکیبی "
            "از یادآوری سه کلمه و ترسیم ساعت (CDT) است تا به‌سرعت حافظه، عملکرد اجرایی و مهارت‌های بصری-فضایی را "
            "ارزیابی کند، تعصب‌های فرهنگی/آموزشی را کاهش داده و زمان نیاز به بررسی عمیق‌تر را نشان دهد."
            if fa
            else "The Mini-Cog is a fast (3-minute) and simple cognitive screening tool used primarily for older adults "
            "to detect potential early dementia or cognitive impairment, combining a three-word memory recall test with a "
            "clock-drawing test (CDT) to quickly assess memory, executive function, and visuospatial skills, minimizing "
            "cultural/educational bias and indicating when further in-depth evaluation is needed."
        )
        self.title.setText("مینی کاگ" if fa else "Mini-Cog")
        self.btn_start.setText("شروع" if fa else "Start")
        heading = "مینی کاگ" if fa else "Mini-Cog"
        header_html = (
            f"<div style='font-size:20px; font-weight:600; text-align:center;'>{heading}</div>"
        )
        body_html = f"<div style='margin-top:6px; text-align:center;'>{description}</div>"
        self.set_instruction_status_text(header_html + body_html)

    def _start(self) -> None:
        self.ctx.controller.start_new_session(language=self.ctx.config.language)
        self.router.go("basic_info")
