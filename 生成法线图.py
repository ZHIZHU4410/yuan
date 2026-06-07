import cv2
import numpy as np
import os
import glob

# ====== 可调参数 ======
STRENGTH = 0.0          # 细节缩放，0 = 无凹凸，1.0 = 标准强度
INVERT_Y = False        # 反转 Y 轴（匹配不同坐标系统）
BLUR_KERNEL = 0         # 模糊大小，0 = 不模糊（若>0则应用高斯模糊）
# ====================

def fill_transparent_area(bgr_img, alpha_mask):
    """
    用非透明区域的像素填充透明区域，防止梯度突变
    bgr_img: BGR图像 (uint8)
    alpha_mask: 单通道alpha (uint8, 0=透明, 255=不透明)
    返回填充后的BGR图像
    """
    # 创建一个修复用的mask（透明区域为白色）
    mask = cv2.bitwise_not(alpha_mask)
    # 使用inpaint填充
    filled = cv2.inpaint(bgr_img, mask, inpaintRadius=3, flags=cv2.INPAINT_TELEA)
    return filled

def gen_normal_map_from_height(height_img_path, output_path,
                               strength=1.0, invert_y=False, blur=0):
    """
    从高度图生成法线贴图
    """
    # 读取图像（保留alpha）
    img = cv2.imread(height_img_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        print(f"  ❌ 无法读取: {height_img_path}")
        return

    has_alpha = (img.shape[2] == 4) if len(img.shape) == 3 else False
    alpha = img[:, :, 3].copy() if has_alpha else None

    # 提取BGR部分（若无alpha则整个图像）
    bgr = img[:, :, :3] if has_alpha else img
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    # 处理透明区域：填充使其高度连续
    if has_alpha:
        alpha_bin = (alpha > 0).astype(np.uint8) * 255
        # 将透明区域像素用周围像素填充
        bgr_filled = fill_transparent_area(bgr, alpha_bin)
        gray_filled = cv2.cvtColor(bgr_filled, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    else:
        gray_filled = gray

    # 模糊（可选）
    if blur > 0:
        gray_filled = cv2.GaussianBlur(gray_filled, (blur, blur), 0)

    # 计算梯度
    grad_x = cv2.Sobel(gray_filled, cv2.CV_32F, 1, 0, ksize=3) * strength
    grad_y = cv2.Sobel(gray_filled, cv2.CV_32F, 0, 1, ksize=3) * strength
    if invert_y:
        grad_y = -grad_y

    # 构建法线向量
    normal = np.zeros((gray.shape[0], gray.shape[1], 3), dtype=np.float32)
    normal[..., 0] = -grad_x
    normal[..., 1] = -grad_y
    normal[..., 2] = 1.0
    norm = np.sqrt(np.sum(normal**2, axis=2, keepdims=True))
    normal = normal / (norm + 1e-8)

    # 编码为颜色值
    normal_vis = ((normal + 1.0) / 2.0 * 255.0).astype(np.uint8)  # [0,255] RGB

    # 透明区域：将法线颜色设为平坦蓝(128,128,255)，alpha=0
    if has_alpha:
        flat_color = np.array([128, 128, 255], dtype=np.uint8)  # BGR对应平坦法线
        mask_zero = (alpha == 0)
        normal_vis[mask_zero] = flat_color[::-1]  # RGB -> BGR
        # 合成带alpha的输出图像
        output_bgra = np.dstack((normal_vis[:, :, ::-1], alpha))  # normal_vis是RGB，先转BGR再拼alpha
    else:
        output_bgra = normal_vis[:, :, ::-1]  # RGB -> BGR

    cv2.imwrite(output_path, output_bgra)
    print(f"  ✅ 已生成: {output_path}")

if __name__ == "__main__":
    folder = input("请输入包含高度图的文件夹路径: ").strip()
    if not os.path.isdir(folder):
        print("路径不存在！")
        exit()

    # 获取所有png图片，排除已有的_n.png
    all_pngs = glob.glob(os.path.join(folder, "*.png"))
    height_files = [f for f in all_pngs if not f.endswith("_n.png")]

    if not height_files:
        print("未找到任何需要处理的高度图。")
        exit()

    print(f"找到 {len(height_files)} 个文件，开始生成法线...\n"
          f"当前参数: 强度={STRENGTH}, 模糊={BLUR_KERNEL}, 反转Y={INVERT_Y}")

    for file_path in height_files:
        base = os.path.basename(file_path)
        name, _ = os.path.splitext(base)
        out_path = os.path.join(folder, name + "_n.png")
        gen_normal_map_from_height(
            file_path, out_path,
            strength=STRENGTH,
            invert_y=INVERT_Y,
            blur=BLUR_KERNEL
        )

    print("\n全部处理完成！")