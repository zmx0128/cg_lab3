# 贝塞尔曲线和B样条曲线

## 📋 项目简介
这是一个使用 Taichi 库实现的交互式曲线绘制系统，展示了如何实现贝塞尔曲线和B样条曲线的绘制，以及反走样技术的应用。

## ✨ 功能特性

1. **贝塞尔曲线绘制**：使用 De Casteljau 算法递归生成曲线点
2. **B样条曲线绘制**：支持均匀三次B样条曲线绘制
3. **清空画布**：支持一键重置画布
4. **模式切换**：通过键盘按键在贝塞尔曲线和B样条曲线之间切换


## 📁 项目结构
```
cg_lab3/
├── src/
│   └── Work3/
│       ├── main.py       # 基础模式（贝塞尔曲线）
│       └── main2.py      # 高级模式（反走样 + B样条曲线）
├── .gitignore         
├── .python-version    
├── pyproject.toml     
├── uv.lock            
└── README.md          # 项目说明文档
```

## 🚀 环境配置
### 1. 创建并激活Conda虚拟环境

```bash
conda create -n cg_env python=3.12 -y
conda activate cg_env 
```

### 2. 安装依赖

在激活的环境中安装`Taichi`：

```bash
# 安装依赖
pip install taichi
```
### 3.IDE配置

## 🎮 使用方法

### 运行基础模式
```bash
uv run python src/Work3/main.py
```

### 运行高级模式
```bash
uv run python src/Work3/main2.py
```

## ⌨️ 按键控制

| 操作 | 说明 |
|------|------|
| 左键点击 | 添加控制点 |
| 按下 `c` 键 | 清空画布 |
| 按下 `b` 键 | 切换曲线模式（贝塞尔 ↔ B样条） |

## 📄 技术文档

### 反走样原理
项目使用了基于距离的反走样技术：
1. 对曲线上的每个采样点，计算其周围3x3像素邻域
2. 计算每个像素中心到曲线点的距离
3. 使用高斯函数计算颜色权重
4. 根据权重混合颜色，实现平滑边缘效果

### B样条曲线原理
项目使用了三次B样条的矩阵形式：

```python
# 三次B样条基矩阵
basis_matrix = np.array([
    [-1, 3, -3, 1],
    [3, -6, 3, 0],
    [-3, 0, 3, 0],
    [1, 4, 1, 0]
]) / 6.0

# 计算点
point = t_vec @ basis_matrix @ p
```

每4个相邻控制点构成一段曲线，n个控制点生成n-3段平滑曲线。

## 🎨 视觉效果

### 基础模式
1. 贝塞尔曲线：粉紫色  
2. 控制点：粉白色  
3. 控制点连线：浅粉色  
4. 曲线边缘：未应用反走样，可能会有轻微锯齿  

<img src="https://github.com/user-attachments/assets/d34e6e06-4c15-4542-a67a-ea5f02dd278e" width="400">

### 高级模式
1. 贝塞尔曲线：冰蓝色  
2. B样条曲线：橙色  
3. 控制点：贝塞尔模式为白色，B样条模式为奶油色  
4. 曲线边缘：应用反走样，边缘平滑无锯齿  

<img src="https://github.com/user-attachments/assets/9ffe6a73-b54c-44c8-9bfa-1a800f889cb4" width="400">


## 🔧 依赖项

1. **Python 3.8+**
2. **Taichi 1.7.4+**：用于并行计算和GUI渲染
3. **NumPy**：用于矩阵运算

