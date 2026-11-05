"""Main menu, language/fullscreen toggles and mouse click routing; mixed into Game."""
import hud
import locale as L
import save
import ui


MENU_ITEMS = 7


class MenuMixin:
    def menu_move(self, d):
        self.menu_sel = (self.menu_sel + d) % MENU_ITEMS

    def toggle_lang(self):
        nxt = "en" if L.lang() == "ru" else "ru"
        L.set_lang(nxt)
        self.lang = nxt
        save.write_settings({"lang": nxt, "fullscreen": self.fullscreen})

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        save.write_settings({"lang": self.lang, "fullscreen": self.fullscreen})

    def menu_act(self, i):
        if i == 0:
            self.new_run()
        elif i == 1:
            self.toggle_lang()
        elif i == 2:
            self.toggle_fullscreen()
        elif i == 3:
            self.state = "controls"
        elif i == 4:
            self.state = "records"
        elif i == 5:
            self.state = "book"
        elif i == 6:
            self.quit = True

    def mouse_click(self, x, y):
        """Route one logical-coordinate click to the UI of the current state."""
        if self.state == "menu":
            i = ui.hit(hud.menu_rects(), (x, y))
            if i is not None:
                self.menu_act(i)
        elif self.state in ("controls", "records", "book"):
            if hud.back_rect().collidepoint(int(x), int(y)):
                self.state = "menu"
        elif self.state == "levelup":
            i = ui.hit(hud.card_rects(len(self.cards)), (x, y))
            if i is not None:
                self.choose_card(i)
        elif self.state == "pause":
            i = ui.hit(hud.pause_rects(), (x, y))
            if i == 0:
                self.state = "play"
            elif i == 1:
                self.new_run()
            elif i == 2:
                self.state = "menu"
        elif self.state in ("over", "win"):
            i = ui.hit(hud.over_rects(), (x, y))
            if i == 0:
                self.new_run()
            elif i == 1:
                self.state = "menu"
