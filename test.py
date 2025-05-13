from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Static
from textual.containers import Container, Grid, Vertical
from textual.widget import Widget
from rich.panel import Panel
from rich.table import Table

class StatusBar(Static):
    def render(self):
        return Panel("Jobs: 15 | Page: 1/3 | Selected: None", title="Status", style="bold cyan")

class JobTable(Static):
    def render(self):
        table = Table(title="Job Listings")
        table.add_column("Company", style="magenta")
        table.add_column("Title", style="green")
        table.add_column("Location")
        table.add_row("Acme Corp", "Engineer", "Remote")
        table.add_row("Beta LLC", "DevOps", "NYC")
        table.add_row("Gamma Inc", "Designer", "SF")
        return table

class JobDetail(Static):
    def render(self):
        return Panel(
            "Company: Acme Corp\nTitle: Engineer\nLocation: Remote\nPosted: 2024-01-01",
            title="Job Details",
            border_style="yellow",
        )

class ScreenshotDemoApp(App):
    BINDINGS = [("s", "save_svg", "Save SVG Screenshot")]

    CSS = """
    Screen {
        align: center middle;
        padding: 1;
    }

    #main {
        height: 1fr;
    }

    #content {
        grid-size: 2;
        grid-gutter: 2;
        height: auto;
    }

    Static {
        border: round white;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="main"):
            yield StatusBar()
            with Grid(id="content"):
                yield JobTable()
                yield JobDetail()
        yield Footer()

    def action_save_svg(self) -> None:
        path = "screenshot.svg"
        self.save_screenshot(path)
        self.notify(f"Saved SVG screenshot to {path}", severity="information")

if __name__ == "__main__":
    ScreenshotDemoApp().run()
