import taichi as ti
import numpy as np

# 使用 gpu 后端
ti.init(arch=ti.gpu)

WIDTH = 800
HEIGHT = 800
MAX_CONTROL_POINTS = 100
NUM_SEGMENTS = 1000  # 曲线采样点数量

# 像素缓冲区
pixels = ti.Vector.field(3, dtype=ti.f32, shape=(WIDTH, HEIGHT))

# GUI 绘制数据缓冲池
gui_points = ti.Vector.field(2, dtype=ti.f32, shape=MAX_CONTROL_POINTS)
gui_indices = ti.field(dtype=ti.i32, shape=MAX_CONTROL_POINTS * 2)

# 曲线坐标的 GPU 缓冲区
curve_points_field = ti.Vector.field(2, dtype=ti.f32, shape=NUM_SEGMENTS + 1)


def de_casteljau(points, t):
    """纯 Python 递归实现 De Casteljau 算法"""
    if len(points) == 1:
        return points[0]
    next_points = []
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        x = (1.0 - t) * p0[0] + t * p1[0]
        y = (1.0 - t) * p0[1] + t * p1[1]
        next_points.append([x, y])
    return de_casteljau(next_points, t)


def cubic_bspline(points, t):
    """三次 B 样条曲线计算"""
    if len(points) < 4:
        return points[0] if points else [0, 0]

    # 三次 B 样条基矩阵
    basis_matrix = np.array(
        [[-1, 3, -3, 1], [3, -6, 3, 0], [-3, 0, 3, 0], [1, 4, 1, 0]]
    ) / 6.0

    # 控制点矩阵
    p = np.array(points)

    # 参数向量
    t_vec = np.array([t**3, t**2, t, 1])

    # 计算点
    point = t_vec @ basis_matrix @ p
    return point


@ti.kernel
def clear_pixels():
    """并行清空像素缓冲区"""
    for i, j in pixels:
        pixels[i, j] = ti.Vector([0.0, 0.0, 0.0])


@ti.kernel
def draw_curve_aa(n: ti.i32, color: ti.template()):
    """反走样绘制 - 使用3x3邻域和高斯距离衰减"""
    for i in range(n):
        pt = curve_points_field[i]
        x = pt[0] * WIDTH
        y = pt[1] * HEIGHT

        # 计算中心像素坐标
        x0 = ti.cast(ti.floor(x), ti.i32)
        y0 = ti.cast(ti.floor(y), ti.i32)

        # 遍历3x3邻域
        for dx in ti.static(range(-1, 2)):
            for dy in ti.static(range(-1, 2)):
                px = x0 + dx
                py = y0 + dy

                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    # 计算像素中心到曲线点的距离
                    pixel_center_x = px + 0.5
                    pixel_center_y = py + 0.5
                    distance = ti.sqrt(
                        (x - pixel_center_x) ** 2 + (y - pixel_center_y) ** 2
                    )

                    # 基于距离衰减模型（高斯函数）
                    # 距离越近，光强贡献越大
                    if distance < 2.0:
                        weight = ti.exp(-distance**2 / 0.5)
                        # 色彩混合实现平滑过渡
                        pixels[px, py] = pixels[px, py] + weight * color


def generate_b_spline_points(control_points):
    """
    生成B样条曲线点 - 严格实现n个控制点生成n-3段曲线
    每4个相邻控制点构成一段曲线
    """
    if len(control_points) < 4:
        return None

    # n个控制点生成n-3段曲线
    num_segments = len(control_points) - 3

    # 每段曲线的采样点数
    points_per_segment = NUM_SEGMENTS // num_segments

    # 计算总点数（避免段间重复）
    total_points = num_segments * points_per_segment + 1

    curve_points = []

    for seg in range(num_segments):
        # 每段使用4个相邻控制点
        seg_points = control_points[seg : seg + 4]

        # 生成该段的采样点
        for t_int in range(points_per_segment):
            t = t_int / points_per_segment
            point = cubic_bspline(seg_points, t)
            curve_points.append(point)

    # 添加最后一段的终点
    last_seg_points = control_points[-4:]
    curve_points.append(cubic_bspline(last_seg_points, 1.0))

    return np.array(curve_points, dtype=np.float32)


def main():
    window = ti.ui.Window("Advanced Curve (AA + B-Spline)", (WIDTH, HEIGHT))
    canvas = window.get_canvas()
    control_points = []
    mode = "bezier"  # 'bezier' or 'bspline'

    while window.running:
        for e in window.get_events(ti.ui.PRESS):
            if e.key == ti.ui.LMB:
                if len(control_points) < MAX_CONTROL_POINTS:
                    pos = window.get_cursor_pos()
                    control_points.append(pos)
                    print(f"Added control point: {pos}, total: {len(control_points)}")
            elif e.key == "c":
                control_points = []
                print("Canvas cleared.")
            elif e.key == "b":
                mode = "bspline" if mode == "bezier" else "bezier"
                print(f"Switched to {mode} mode")

        clear_pixels()

        current_count = len(control_points)
        if current_count >= 2:
            if mode == "bezier":
                # 贝塞尔曲线
                curve_points_np = np.zeros((NUM_SEGMENTS + 1, 2), dtype=np.float32)
                for t_int in range(NUM_SEGMENTS + 1):
                    t = t_int / NUM_SEGMENTS
                    curve_points_np[t_int] = de_casteljau(control_points, t)

                # 绘制曲线（带反走样）- 冰蓝色
                curve_points_field.from_numpy(curve_points_np)
                color = ti.Vector([0.4, 0.7, 1.0])
                draw_curve_aa(len(curve_points_np), color)

            else:
                # B样条曲线
                if current_count >= 4:
                    # 生成B样条曲线点 - n个控制点生成n-3段曲线
                    curve_points_np = generate_b_spline_points(control_points)

                    if curve_points_np is not None:
                        print(
                            f"B-Spline: {current_count} control points, "
                            f"{current_count - 3} segments, "
                            f"{len(curve_points_np)} curve points"
                        )

                        # 确保不超出缓冲区大小
                        if len(curve_points_np) > NUM_SEGMENTS + 1:
                            curve_points_np = curve_points_np[: NUM_SEGMENTS + 1]

                        # 绘制曲线（带反走样）- 橙色
                        curve_points_field.from_numpy(curve_points_np)
                        color = ti.Vector([1.0, 0.5, 0.0])
                        draw_curve_aa(len(curve_points_np), color)
                else:
                    # 控制点不足4个时，提示用户
                    print(
                        f"B-Spline requires at least 4 control points, "
                        f"currently have {current_count}"
                    )

        canvas.set_image(pixels)

        if current_count > 0:
            np_points = np.full((MAX_CONTROL_POINTS, 2), -10.0, dtype=np.float32)
            np_points[:current_count] = np.array(control_points, dtype=np.float32)
            gui_points.from_numpy(np_points)

            # 根据模式显示不同颜色的控制点
            if mode == "bezier":
                point_color = (1.0, 1.0, 1.0)  # 白色
                line_color = (0.6, 0.7, 0.9)  # 浅冰蓝色
            else:
                point_color = (1.0, 0.85, 0.6)  # 奶油色
                line_color = (0.7, 0.5, 0.3)  # 咖啡色

            canvas.circles(gui_points, radius=0.005, color=point_color)

            if current_count >= 2:
                np_indices = np.zeros(MAX_CONTROL_POINTS * 2, dtype=np.int32)
                indices = []
                for i in range(current_count - 1):
                    indices.extend([i, i + 1])
                np_indices[: len(indices)] = np.array(indices, dtype=np.int32)
                gui_indices.from_numpy(np_indices)
                canvas.lines(
                    gui_points, width=0.002, indices=gui_indices, color=line_color
                )

        window.show()


if __name__ == "__main__":
    main()
