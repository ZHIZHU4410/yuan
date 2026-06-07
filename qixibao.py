import copy
import json
import sys

# ========== 配置 ==========
INPUT_FILE = "data.cdb"
OUTPUT_FILE = "data_modified.cdb"
NEW_BCS = [6, 7]
USE_EXPONENTIAL_SCALE = True
BASE_SCALE = 1.15

BC_NAMES = {6: "Hell", 7: "Inferno", 8: "Apocalypse", 9: "Cataclysm", 10: "Nightmare"}

# ========== 工具 ==========
def calc_scale(level):
    if USE_EXPONENTIAL_SCALE:
        return BASE_SCALE ** (level - 5)
    else:
        return 1.0 + (level - 5) * 0.25

# ========== 主逻辑 ==========
def main():
    print(f"加载 {INPUT_FILE} ...")
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        db = json.load(f)

    # 检查结构
    if not isinstance(db, dict) or "sheets" not in db:
        print("错误：顶层没有 'sheets' 键")
        sys.exit(1)

    sheets = db["sheets"]
    if not isinstance(sheets, list):
        print("错误：sheets 不是数组")
        sys.exit(1)

    # 找到 difficulty 工作表
    difficulty_sheet = None
    for sheet in sheets:
        if sheet.get("name") == "difficulty":
            difficulty_sheet = sheet
            break

    if difficulty_sheet is None:
        print("错误：未找到 name='difficulty' 的工作表")
        sys.exit(1)

    lines = difficulty_sheet.get("lines")
    if not isinstance(lines, list):
        print("错误：difficulty 工作表中没有 lines 数组")
        sys.exit(1)

    print(f"找到 difficulty 工作表，共 {len(lines)} 行")

    # 找到 5BC 模板
    base_5bc = None
    for row in lines:
        if row.get("difficultyLevel") == 5:
            base_5bc = copy.deepcopy(row)
            break

    if base_5bc is None:
        print("错误：未找到 difficultyLevel=5 的配置")
        sys.exit(1)

    print("已找到 5BC 模板")

    # 移除已存在的目标难度（避免重复）
    lines[:] = [row for row in lines if row.get("difficultyLevel") not in NEW_BCS]

    # 生成新难度
    for bc in NEW_BCS:
        print(f"\n生成 {bc}BC ...")
        new = copy.deepcopy(base_5bc)
        scale = calc_scale(bc)
        print(f"  缩放系数 = {scale:.4f}")

        new["difficultyLevel"] = bc
        if "id" in new:
            new["id"] = BC_NAMES.get(bc, f"CustomBC_{bc}")

        # 字段调整
        if "extraMobDensity" in new:
            new["extraMobDensity"] = round(new["extraMobDensity"] * scale * 1.4, 3)
        if "bossExtraLife" in new:
            new["bossExtraLife"] = round(new["bossExtraLife"] * scale * 1.5, 3)

        delta = bc - 5
        if "extraAtkTiers" in new:
            new["extraAtkTiers"] += delta * 2
        if "extraElitesPerLevel" in new:
            new["extraElitesPerLevel"] += delta * 2
        if "aggressiveMobs" in new:
            new["aggressiveMobs"] = True
        if "malaise" in new:
            new["malaise"] = True

        if "levelSettings" in new and isinstance(new["levelSettings"], list):
            for lvl in new["levelSettings"]:
                if "mobAtkTier" in lvl:
                    lvl["mobAtkTier"] += delta * 6
                if "mobLifeTier" in lvl:
                    lvl["mobLifeTier"] += delta * 8
                if "extraLevel" in lvl:
                    lvl["extraLevel"] += delta
                if "eliteChance" in lvl:
                    lvl["eliteChance"] = min(1.0, lvl["eliteChance"] + delta * 0.08)

        lines.append(new)
        print(f"  {bc}BC 已添加")

    # 按难度等级排序（可选）
    lines.sort(key=lambda x: x.get("difficultyLevel", 0))

    # 解除其他工作表中的等级上限
    print("\n尝试解除等级上限...")
    target_sheet_names = {"balance", "globalBalance", "gameBalance", "mobBalance"}
    for sheet in sheets:
        if sheet.get("name") in target_sheet_names:
            if "lines" in sheet and isinstance(sheet["lines"], list):
                for row in sheet["lines"]:
                    for key in ["maxMobTier", "maxScalingTier", "maxDifficulty", "difficultyCap"]:
                        if key in row:
                            row[key] = 999
    print("完成解除")

    # 保存
    print(f"保存到 {OUTPUT_FILE} ...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, indent=2, ensure_ascii=False)
    print("完成！")

if __name__ == "__main__":
    main()