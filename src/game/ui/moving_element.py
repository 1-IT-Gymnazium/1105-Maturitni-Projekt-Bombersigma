import math
import pygame


class MovingElement:
    def __init__(self, image, start_pos, target_pos, duration_ms=600):
        self.base_image = image
        self.image = image

        self.start_pos = pygame.Vector2(start_pos)
        self.target_pos = pygame.Vector2(target_pos)
        self.pos = pygame.Vector2(start_pos)

        self.duration_ms = duration_ms
        self.elapsed_ms = 0
        self.finished = False

    def update(self, dt):
        if self.finished:
            return True

        self.elapsed_ms += dt
        t = min(1.0, self.elapsed_ms / self.duration_ms)
        t = 1 - (1 - t) ** 3

        self.pos = self.start_pos.lerp(self.target_pos, t)

        if self.elapsed_ms >= self.duration_ms:
            self.pos = pygame.Vector2(self.target_pos)
            self.finished = True
            return True

        return False

    def draw(self, surface):
        rect = self.image.get_rect(center=(round(self.pos.x), round(self.pos.y)))
        surface.blit(self.image, rect)

    def set_image(self, image):
        self.base_image = image
        self.image = image

    def reset(self):
        self.pos = pygame.Vector2(self.start_pos)
        self.elapsed_ms = 0
        self.finished = False


class MovingButton(MovingElement):
    def __init__(self, button, start_pos, target_pos, duration_ms=600):
        super().__init__(button.image, start_pos, target_pos, duration_ms)
        self.button = button
        self.button.rect.center = (round(self.pos.x), round(self.pos.y))

    def update(self, dt):
        finished = super().update(dt)
        self.button.rect.center = (round(self.pos.x), round(self.pos.y))
        return finished

    def draw(self, surface):
        self.button.draw(surface)

    def handle_event(self, event):
        self.button.handle_event(event)

    def reset(self):
        super().reset()
        self.button.rect.center = (round(self.pos.x), round(self.pos.y))


class WinnerArrow(MovingElement): #EVERYTHING IN THIS CLASS IS MADE BY CHATGPT I TAKE ZERO CREDIT
    def __init__(self, image, duration_ms=600):
        super().__init__(image, (0, 0), (0, 0), duration_ms)

    def configure(self, winner_text, winner_player, arrow_image):
        self.base_image = arrow_image

        tail_pos, target_pos = self._get_tail_and_target(winner_text, winner_player)

        scaled_image, target_center = self._build_transformed_arrow(
            arrow_image,
            tail_pos,
            target_pos
        )

        self.image = scaled_image
        self.start_pos = pygame.Vector2(target_center.x, target_center.y + 500)
        self.target_pos = pygame.Vector2(target_center)
        self.pos = pygame.Vector2(self.start_pos)

        self.elapsed_ms = 0
        self.finished = False

    def _get_tail_and_target(self, winner_text, winner_player):
        text_w = winner_text.image.get_width()

        # start the arrow on the winner_text, about 25% of its width from the left edge
        left_edge_x = winner_text.target_pos.x - text_w / 2
        tail_x = left_edge_x + text_w * 0.25
        tail_y = winner_text.target_pos.y

        tail_pos = pygame.Vector2(tail_x, tail_y)

        # point to the center of the winner sprite
        player_center_x = winner_player.target_pos[0] + winner_player.sprite.get_width() / 2
        player_center_y = winner_player.target_pos[1] + winner_player.sprite.get_height() / 2

        target_pos = pygame.Vector2(player_center_x, player_center_y)
        return tail_pos, target_pos

    def _build_transformed_arrow(self, arrow_image, tail_pos, target_pos):
        vec = target_pos - tail_pos
        distance = vec.length()

        if distance == 0:
            return arrow_image, tail_pos

        base_w = arrow_image.get_width()
        base_h = arrow_image.get_height()
        base_diag = math.hypot(base_w, base_h)

        scale = distance / base_diag
        new_w = max(1, round(base_w * scale))
        new_h = max(1, round(base_h * scale))
        scaled = pygame.transform.smoothscale(arrow_image, (new_w, new_h))

        # default direction of the source arrow image:
        # bottom-left -> top-right
        base_angle = math.degrees(math.atan2(new_h, new_w))

        # pygame screen coords: y grows downward
        desired_angle = math.degrees(math.atan2(-(vec.y), vec.x))
        rotation = desired_angle - base_angle

        rotated = pygame.transform.rotate(scaled, rotation)

        # figure out where the rotated image center must be so that
        # the arrow's bottom-left corner sits exactly on tail_pos
        local_bottom_left = pygame.Vector2(-new_w / 2, new_h / 2)
        rotated_offset = local_bottom_left.rotate(-rotation)
        image_center = tail_pos - rotated_offset

        return rotated, image_center
