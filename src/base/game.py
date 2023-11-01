import pygame
import pytmx
import sys
from pytmx.util_pygame import load_pygame

from src.enemy import enemy_script
from src.enemy.unit.enemy import Enemy
from src.enemy.weapon.enemy_wpn import EnemyWeapon
from src.misc import *
from src.player.unit.player import Player
from src.player.weapon.player_wpn import PlayerWeapon

# 定数
RESET_COOLDOWN = 10  # プレイヤーの武器の射撃間隔
FPS = 10    # フレームレート？
FPS_CLOCK = pygame.time.Clock()
BLACK = pygame.Color(0, 0, 0)


def scroll_hitbox(surface, tiled_map, hitbox, scroll_x, debug=0):
    
    hitbox.empty()   # スクロール更新

    for layer in tiled_map.visible_layers:
        if isinstance(layer, pytmx.TiledObjectGroup):
            
            for obj in layer:
                if debug:
                    spr = Block(
                        (obj.x + scroll_x, obj.y, obj.width, obj.height)
                    )
                    pygame.draw.rect(surface, (0, 0, 255),
                        (obj.x + scroll_x, obj.y, obj.width, obj.height))
                else:
                    spr = Block(
                        (obj.x + scroll_x, obj.y, obj.width, obj.height)
                    )

                hitbox.add(spr)


def update_projectiles(surface, projectiles, hitbox, debug=0):

    for projectile in projectiles:
        if projectile.charging:
            projectile.draw(surface)
        elif not projectile.charging and \
                len(pygame.sprite.spritecollide(projectile, hitbox, False, collision_projectile)) == 0 \
                and not projectile.out_of_screen and not projectile.dead:
            if isinstance(projectile, EnemyWeapon):
                hitbox.add(projectile)
            projectile.draw(surface)
            projectile.move()
            if debug:
                pygame.draw.rect(surface, (0, 0, 255),
                                 (projectile.rect.x,
                                  projectile.rect.y,
                                  projectile.image.get_width(),
                                  projectile.image.get_height()
                                  )
                                 )
        else:
            if not projectile.dead and isinstance(projectile, PlayerWeapon):
                projectile.impact(surface)
            else:
                projectiles.remove(projectile)


def collision_projectile(projectile, target):

    if pygame.sprite.collide_rect(projectile, target):
        # ユニットの発射物が敵に当たった場合...
        if isinstance(projectile, PlayerWeapon) and isinstance(target, Enemy):
            if target.invincible:
                return False
            else:
                target.take_damage(projectile.damage)

            projectile.draw_impact = False
            if projectile.damage < 13:  # 敵が倒されるまでビームは貫通しない
                projectile.dead = True
            if target.dead:  # 敵が倒されたらビームを貫通させる
                return False

        # 敵の発射物が接触した場合、敵は倒されない
        elif isinstance(projectile, EnemyWeapon) and isinstance(target, Enemy):
            return False

        # ユニットの発射物と敵の発射物は互いに通過する
        elif isinstance(projectile, PlayerWeapon) and isinstance(target, EnemyWeapon):
            return False

        # 敵の発射物や他の敵の発射物も同様
        elif isinstance(projectile, EnemyWeapon) and isinstance(target, EnemyWeapon):
            return False

        projectile.collide_distance = target.rect.x - projectile.rect.x
        return True
    else:
        return False


def player_handler(surface, player, hitbox, scroll):

    if len(pygame.sprite.spritecollide(player, hitbox, False, pygame.sprite.collide_mask)) > 0:
        if not player.invincible:
            player.death()
        else:
            if scroll:
                player.rect.x = player.last_pos[0] - 1  # 自動右スクロール画面を補正するためのオフセット
            else:
                player.rect.x = player.last_pos[0]
            player.rect.y = player.last_pos[1]


def enemy_handler(surface, player, enemies, hitbox, scroll):

    for enemy in enemies:
        if scroll:
            enemy.move(-1, 0)  # スクロール画面の補正
        if enemy.dead_counter == 0:
            hitbox.add(enemy)

        if player.rect.x - enemy.rect.x > surface.get_width():  # ユニットが敵を十分に通過した場合、敵は消滅します
            enemy.death(sound=False)  # 敵にdead_counterを開始

        if enemy.dead_counter < enemy.dead_counter_max:
            enemy.draw(surface)
        else:
            enemies.remove(enemy)


def player_keys_move(surface, player, keys):

    vx, vy = 0, 0
    player.last_pos = (player.rect.x, player.rect.y)

    #　プレーヤーユニットの移動？
    if keys[pygame.K_UP]:
        vy -= 50
    elif keys[pygame.K_DOWN]:
        vy += 50

    if keys[pygame.K_LEFT]:
        vx -= 50
    elif keys[pygame.K_RIGHT]:
        vx += 50

    player.move(surface, vx, vy)


def player_keys_shoot(surface, player, keys, projectiles, cooldown_counter):

    if keys[pygame.K_SPACE] and not player.charged_beam:
        if cooldown_counter == 1 and not player.dead:   # クールダウン完了 AND プレーヤーが生きている？
            projectiles.add(
                player.shoot(player.rect.x+player.image.get_width(), player.rect.y+player.image.get_height()/2)
            )
            cooldown_counter += 1  # クールダウンを開始
    elif keys[pygame.K_e]:
        if not player.charged_beam and not player.dead:
            projectiles.add(
                player.shoot(player.rect.x+player.image.get_width()-5, player.rect.y+player.image.get_height()/2, True)
            )
    else:
        if player.charged_beam:
            player.charged_beam.charging = False  # キーが押されていない場合は充電をリセット
        player.charged_beam = None  # チャージビーム削除

    # cooldown_counterが規定値に達したらリセット
    if cooldown_counter == RESET_COOLDOWN:
        cooldown_counter = 0
    elif cooldown_counter > 0:
        cooldown_counter += 1
    return cooldown_counter


def start_level(surface):
    # 現在のウィンドウを再設定する
    surface.fill((0, 0, 0))  # 画面をワイプ
    bg = pygame.image.load("img/stage.png").convert()
    ready_logo = pygame.image.load("img/ready.gif").convert()
    game_over_logo = pygame.image.load("img/game_over.gif").convert()

    # 音楽を設定
    pygame.mixer.music.load('sounds/music/solo_sortie.mp3')

    # サウンドを設定
    victory_tune = pygame.mixer.Sound('sounds/victory.wav')

    # 初期スプライトを設定
    hitbox = pygame.sprite.Group()
    projectiles = pygame.sprite.Group()

    player = Player(100, 280)  # ユニット初期位置　x = 100, y = 280
    player.draw(surface)

    # ゲームの設定
    lives = 3  # 残機 デフォルトは３
    scroll = True  # 画面をスクロールする必要があるかどうかを示します。これは横スクロールゲームなのでTrue
    scroll_x = 0  # 背景タイルマップの現在のスクロール量を示す。値が小さいほど、遠くなる
    game_start = True  # 最初のプレイスルーの前にチェックされるフラグ

    # ゲームの一時停止はユーザーが原因で発生　ボスの一時停止は、ゲームイベントによってトリガーされる
    game_pause, boss_pause = False, False  # ゲームを一時停止するフラグ

    player_lock = False  # ユニットのキーボードアクションのみをロック
    boss_timer = 0  # 上司のアクションシーケンスを追跡するタイマー（enemy_script.pyを参照）
    boss_pause_timer, win_pause_timer = 0, 0  # ゲームイベントによって引き起こされる一時停止のタイマー
    round_clear = False  # ゲームの終了を開始するためのフラグ
    play_win_theme = False  # 勝利のテーマソングを再生するためのフラグ

    enemies = enemy_script.create_enemies(surface, scroll_x)

    # カウンター/タイマー
    cooldown_counter = 0  # プレイヤーが攻撃した後の攻撃なしのシーケンス/間隔
    rf_counter = 250  # プレイヤーが死んだ後のラウンドフェイルタイマー

    tiled_map = load_pygame('tilemap/rtype_tile.tmx')  # これは背景のヒットボックスをロードするため、重要

    # アルファ画面（スムーズなフェードイン/フェードアウト用）
    alpha_surface = pygame.Surface((800, 600)) 
    alpha_surface.fill((0, 0, 0))
    alpha = 245
    alpha_surface.set_alpha(alpha)

    while True:  # メインループ
        #  ノーマルイベント
        for event in pygame.event.get():

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # enter key
                    game_pause = not game_pause
                    pygame.mixer.Sound('sounds/start.ogg').play()

        if not game_start and not game_pause:  # ゲームが最初に開始するとき、以下は必要なし
            #  Key Events
            if not player_lock:
                keys = pygame.key.get_pressed()
                player_keys_move(surface, player, keys)
                cooldown_counter = player_keys_shoot(surface, player, keys, projectiles, cooldown_counter)
    
            surface.blit(bg, (scroll_x, 0)) # 背景を+x方向にスクロールする
    
            scroll_hitbox(surface, tiled_map, hitbox, scroll_x)
    
            #  衝突
            enemy_handler(surface, player, enemies, hitbox, scroll)
            update_projectiles(surface, projectiles, hitbox)
            player.draw(surface)
    
            player_handler(surface, player, hitbox, scroll)

            #  UI
            pygame.draw.rect(surface, BLACK, (0, 560, 800, 40))
            for i in range(0, lives):
                lives_ico = Icon(100 + (i * 30), 565)
                lives_ico.draw(surface)

        #  ラウンドを開始
        if player.dead or game_start:
            pygame.mixer.music.stop()
            rf_counter += 1
            if 250 > rf_counter > 200:
                alpha += 6
                alpha_surface.set_alpha(alpha)

            elif 300 > rf_counter > 250:
                scroll_x = 0  # スクロール画面をリセット
                scroll = True
                boss_timer = 0
                if not game_start:
                    lives -= 1 

                if lives == 0:
                    alpha_surface.blit(game_over_logo, (surface.get_width()/2-game_over_logo.get_width()/2,
                                                        surface.get_height()/2-game_over_logo.get_height()/2))
                else:
                    alpha_surface.blit(ready_logo, (surface.get_width()/2-ready_logo.get_width()/2,
                                                    surface.get_height()/2-ready_logo.get_height()/2))

                enemies = enemy_script.create_enemies(surface, scroll_x)  # 新しい敵をスポーン/リスポーンする
                projectiles.empty()
                rf_counter = 300

            elif 400 > rf_counter > 350 and lives > 0:
                alpha_surface.fill((0, 0, 0))
                alpha -= 6
                alpha_surface.set_alpha(alpha)

            elif rf_counter >= 400 and lives > 0:
                pygame.mixer.music.load('sounds/music/solo_sortie.mp3')
                pygame.mixer.music.play(-1, 0.2)  # 音楽を再開
                player.respawn()
                rf_counter = 0
                game_start = False
            elif 600 > rf_counter > 500 and lives == 0:
                alpha_surface.fill((0, 0, 0))
            elif rf_counter > 600 and lives == 0:  # ゲームメニューの最初に戻る
                return

            surface.blit(alpha_surface, (0, 0))
        else:
            if not round_clear:
                alpha = 0

        if not game_start and not game_pause and scroll_x > -5800:
            scroll_x -= 1  # オフセットscroll_xをデクリメントして、背景を右にスクロール
        elif -5850 < scroll_x <= -5800:
            pygame.mixer.music.fadeout(1000)
            scroll_x -= 1
        elif scroll_x <= -5850:
            if scroll:
                pygame.mixer.music.load('sounds/music/boss.mp3')
                pygame.mixer.music.play()
                scroll = False
                boss_pause_timer = 4000 + pygame.time.get_ticks()
                player_lock = True
            if pygame.time.get_ticks() >= boss_pause_timer:
                if player_lock:
                    player_lock = False

                if not game_pause:
                    boss_timer += 1
                    if boss_timer > 300:
                        boss_timer = 1

        #  ステージがクリアされるまで（またはゲームが一時停止されるまで）、敵はスクリプトに従う
        if not round_clear and not game_pause:
            round_clear = enemy_script.load(scroll_x, boss_timer, player, enemies, projectiles)

        if round_clear:
            if not play_win_theme:
                player.be_invincible(animation=False)
                play_win_theme = True
                pygame.time.wait(1000)
                victory_tune.play()
                boss_pause_timer = 6000 + pygame.time.get_ticks()
                alpha_surface.blit(game_over_logo, (surface.get_width()/2-game_over_logo.get_width()/2,
                                                    surface.get_height()/2-game_over_logo.get_height()/2))
            if pygame.time.get_ticks() >= boss_pause_timer:
                alpha += 2
                alpha_surface.set_alpha(alpha)
                surface.blit(alpha_surface, (0, 0))
                if alpha > 800:
                    return

        pygame.display.update()  # すべてのイベントが処理されたら、表示を更新
        FPS_CLOCK.tick(FPS)
