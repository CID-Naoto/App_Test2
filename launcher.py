"""
R-Typo Project
CS332L, Spring 2016
https://github.com/rkenmi/R-Typo

Rick Miyamoto
"""
import os
import sys

import pygame

from src import game
from src.player.unit import Player

FPS = 60

if getattr(sys, 'frozen', False):
    os.chdir(sys._MEIPASS)

def main():
    pygame.init()
    fps_clock = pygame.time.Clock()

    # 初期ウィンドウを作成
    window_size = (800, 600)
    surface = pygame.display.set_mode(window_size)

    # 音楽を設定
    pygame.mixer.music.load('sounds/music/medley.mp3')
    pygame.mixer.music.play(-1, 0.2)

    # ウィンドウのタイトルを設定
    pygame.display.set_caption("CID-FEST")

    # 画像の読み込みと配置
    r_type_logo = pygame.image.load("img/main_logo.png").convert()
    r_type_logo.set_colorkey(pygame.Color(0, 0, 0))
    enter_logo = pygame.image.load("img/x-Enter.gif").convert()
    ship = Player(window_size[0]/2 - 30, window_size[1]/2 - 15)
    
    bg = pygame.image.load("img/space_bg.png")

    # カウンター/タイマー
    text_timer, start_timer = 0, 0

    scroll_x = 0  # スペース画像の現在のスクロール量を示す。 値が小さいほど、遠くなる
    game_ready = False  # プレーヤーがゲームのプレイを開始する準備ができていることを示す
    
    # アルファ画面（スムーズなフェードイン/フェードアウト用）
    alpha_surface = pygame.Surface((800, 600))
    alpha_surface.fill((0, 0, 0))
    alpha_surface.set_alpha(0)
    alpha = 0

    while True:
        surface.fill((0, 0, 0))
        surface.blit(bg, (scroll_x, 0))
        pygame.draw.rect(surface, (0, 0, 0), (0, 0, 800, 200))
        pygame.draw.rect(surface, (0, 0, 0), (0, 400, 800, 200))
        surface.blit(r_type_logo, (window_size[0]/2-r_type_logo.get_width()/2,
                                   window_size[1]/4-r_type_logo.get_height()/2 - 50))

        ship.draw(surface)
        text_timer += 1

        if text_timer < 50:
            surface.blit(enter_logo,
                         (window_size[0]/2-enter_logo.get_width()/2,
                          window_size[1]/2-enter_logo.get_height()/2 + 200))
        elif text_timer > 100:
            text_timer = 0

        scroll_x -= 1
        if scroll_x < -800:
            scroll_x = 0

        if game_ready:
            ship.move(surface, 10, 0, bypass_wall=True)  # アニメーション
            start_timer += 1  # ゲームモードまでカウントダウンを開始
            text_timer = 1 
            if start_timer == 100:
                pygame.mixer.music.fadeout(1000)
            if 200 > start_timer > 100:
                alpha += 5
                alpha_surface.set_alpha(alpha)
            elif start_timer >= 200:
                game.start_level(surface)
                pygame.quit()
                sys.exit()

        for event in pygame.event.get():
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    game_ready = True
                    pygame.mixer.Sound('sounds/start.ogg').play()
                    start_timer = 0

        surface.blit(alpha_surface, (0, 0))
        pygame.display.update()
        fps_clock.tick(FPS)

if __name__ == "__main__":
    main()
