import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Ellipse, Rectangle

FONT = "Tahoma"
plt.rcParams["font.family"] = FONT

W, YMIN, YMAX = 140, -22, 200
fig = plt.figure(figsize=(9.0, 9.0 * (YMAX - YMIN) / W))
ax = fig.add_axes([0, 0, 1, 1])
ax.set_xlim(0, W)
ax.set_ylim(YMIN, YMAX)
ax.axis("off")

C_PROC = ("#EAF2FB", "#2F5D8A")
C_DEC = ("#FFF4DC", "#B7791F")
C_TERM = ("#E6F4EA", "#2E7D32")
C_STOP = ("#FDECEC", "#B23B3B")
C_NOTE = ("#F7F7F7", "#888888")
C_DB = ("#EEE8F7", "#5B3F8C")
FS = 8.6

MX, MW = 63, 58          # main column centre / width
LX, LW = 15, 26          # left column centre / width
RX, RW = 122, 32         # right column centre / width
LOOPX = 98               # loop-back line


def box(x, y, w, h, text, col=C_PROC, fs=FS, round_=1.2, bold=False, ha="center"):
    ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                boxstyle=f"round,pad=0,rounding_size={round_}",
                                fc=col[0], ec=col[1], lw=1.2, zorder=2))
    tx = x if ha == "center" else x - w / 2 + 1.5
    ax.text(tx, y, text, ha=ha, va="center", fontsize=fs, zorder=3,
            fontweight="bold" if bold else "normal", linespacing=1.45)


def term(x, y, w, h, text, col=C_TERM, fs=FS):
    box(x, y, w, h, text, col, fs, round_=h / 2, bold=True)


def diamond(x, y, w, h, text, fs=FS):
    ax.add_patch(Polygon([(x, y + h / 2), (x + w / 2, y), (x, y - h / 2), (x - w / 2, y)],
                         closed=True, fc=C_DEC[0], ec=C_DEC[1], lw=1.2, zorder=2))
    ax.text(x, y, text, ha="center", va="center", fontsize=fs, zorder=3, linespacing=1.4)


def note(x, y, w, h, text, fs=7.6):
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=C_NOTE[0], ec=C_NOTE[1],
                           lw=0.9, ls=(0, (3, 2)), zorder=2))
    ax.text(x - w / 2 + 1.2, y, text, ha="left", va="center", fontsize=fs, zorder=3,
            linespacing=1.45, color="#333333")


def cylinder(x, y, w, h, title, body, fs=7.8):
    e = 4.0
    ax.add_patch(Rectangle((x - w / 2, y - h / 2), w, h, fc=C_DB[0], ec="none", zorder=2))
    ax.plot([x - w / 2, x - w / 2], [y - h / 2, y + h / 2], color=C_DB[1], lw=1.2, zorder=3)
    ax.plot([x + w / 2, x + w / 2], [y - h / 2, y + h / 2], color=C_DB[1], lw=1.2, zorder=3)
    ax.add_patch(Ellipse((x, y - h / 2), w, e, fc=C_DB[0], ec=C_DB[1], lw=1.2, zorder=2))
    ax.add_patch(Rectangle((x - w / 2 + 0.6, y - h / 2), w - 1.2, e / 2 + 0.2, fc=C_DB[0], ec="none", zorder=2))
    ax.add_patch(Ellipse((x, y + h / 2), w, e, fc="#DCD1EE", ec=C_DB[1], lw=1.2, zorder=3))
    ax.text(x, y + h / 2 - 4.2, title, ha="center", va="center", fontsize=8.4,
            fontweight="bold", zorder=4, color=C_DB[1])
    ax.text(x - w / 2 + 1.6, y + h / 2 - 9, body, ha="left", va="top", fontsize=fs,
            zorder=4, linespacing=1.55)


def arrow(pts, label=None, lpos=None, dashed=False, color="#333333", head=True):
    xs, ys = zip(*pts)
    ls = (0, (4, 2.5)) if dashed else "-"
    ax.plot(xs[:-1] + (xs[-1],), ys, color=color, lw=1.1, ls=ls, zorder=1)
    if head:
        ax.annotate("", xy=pts[-1], xytext=pts[-2],
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1,
                                    mutation_scale=11, shrinkA=0, shrinkB=0), zorder=1)
    if label:
        ax.text(*lpos, label, fontsize=8, ha="center", va="center", color=color,
                fontweight="bold", zorder=4,
                bbox=dict(fc="white", ec="none", pad=0.6))


# ---------------- rows ----------------
Y = dict(start=193, prof=180, d1=166, cond=151, loop=137, find=123, d2=109,
         fetch=95, cls=81, alert=68, d3=54, summ=40, adj=24, save=7, send=-6, end=-17)
H = 9

term(MX, Y["start"], MW, 10,
     "เริ่มต้น: รายการชื่อส่วนผสมที่จับคู่ได้\n(ผลจาก OCR + Fuzzy Matching กับ INCI vocabulary, threshold = 85)", fs=8.1)
box(MX, Y["prof"], MW, H,
    "อ่านโปรไฟล์ล่าสุดของผู้ใช้จากฐานข้อมูล\n(ประเภทผิว, การตั้งครรภ์, ผิวเป็นสิวง่าย, สิวเชื้อรา)")
diamond(MX, Y["d1"], 34, 12, "โปรไฟล์ครบและ\nมีประเภทผิว?")
box(MX, Y["cond"], MW, H,
    "กำหนดเงื่อนไขที่ต้องพิจารณาเพิ่มเติมจากโปรไฟล์\n(active_conditions)")
box(MX, Y["loop"], MW, H,
    "พิจารณาส่วนผสมทีละรายการ\n(ตัดชื่อที่ OCR อ่านซ้ำออก)", col=("#E3EEF9", "#2F5D8A"), bold=True)
box(MX, Y["find"], MW, H,
    "ค้นหาชื่อส่วนผสมในตาราง ingredients\n(ไม่สนตัวพิมพ์ / ใช้ชื่อหลักจาก identity mapping เช่น WATER → AQUA)", fs=8.1)
diamond(MX, Y["d2"], 34, 12, "พบส่วนผสม\nในฐานข้อมูล?")
box(MX, Y["fetch"], MW, H,
    "ดึงข้อมูลความรู้ของส่วนผสม\nskin effects (ตามประเภทผิว) · risks · evidence")
box(MX, Y["cls"], MW, H,
    "แยก risk ตามโปรไฟล์ผู้ใช้ (เทียบ risk_type กับเงื่อนไข)\nตรงโปรไฟล์ → profile alert · ไม่ตรง → ข้อมูลประกอบ (other_risks)", fs=8.0)
box(MX, Y["alert"], MW, H,
    "จัดสถานะรายส่วนผสม (classify_ingredient)\nrisk ตรงโปรไฟล์ระดับ low → ควรระวัง · moderate/high → ความเสี่ยง", fs=8.0)
diamond(MX, Y["d3"], 34, 12, "พิจารณาครบ\nทุกรายการ?")
box(MX, Y["summ"], MW, H,
    "สรุปผลภาพรวมของผลิตภัณฑ์ (summarize_product)\nตามลำดับความสำคัญ risk > caution > no_evidence > no_risk_found")
box(MX, Y["adj"], MW, 14,
    "ปรับผลสรุปตามข้อจำกัดของข้อมูล\n"
    "• มีรายการจับคู่ไม่ได้ → ไม่สรุปว่า “ไม่พบความเสี่ยง”\n"
    "• profile alert ระดับ moderate/high → risk · ระดับ low → caution\n"
    "• เงื่อนไขที่ฐานข้อมูลยังไม่ครอบคลุม → แจ้งว่ายังยืนยันไม่ได้\n"
    "• กำหนด suitable และไม่คำนวณ safe_score (ค่าว่าง)", fs=7.9, ha="left")
box(MX, Y["save"], MW, 12,
    "สร้างข้อความผลวิเคราะห์ (ผลรวม, รายส่วนผสม, ข้อควรระวัง,\nรายการที่จับคู่ไม่ได้, หมายเหตุว่าไม่ใช่คำแนะนำทางการแพทย์)\nและบันทึกผลการสแกนลงฐานข้อมูล", fs=8.1)
box(MX, Y["send"], MW, H,
    "ส่งผลสรุปกลับไปยังผู้ใช้ผ่าน LINE Push API\n(แจ้ง “กรุณารอ” ด้วย Reply API ตั้งแต่ได้รับภาพ)\nQuick Reply: “ดูรายละเอียด” / “สแกนขวดอื่นต่อ” / “ตั้งค่าโปรไฟล์”", fs=7.8)
term(MX, Y["end"], 26, 7, "สิ้นสุด")

# ---------------- main flow arrows ----------------
def down(a, b, ha_, hb_, label=None):
    p = [(MX, Y[a] - ha_ / 2), (MX, Y[b] + hb_ / 2)]
    arrow(p, label, (MX + 4, (p[0][1] + p[1][1]) / 2) if label else None)

down("start", "prof", 10, H)
down("prof", "d1", H, 12)
down("d1", "cond", 12, H, "ใช่")
down("cond", "loop", H, H)
down("loop", "find", H, H)
down("find", "d2", H, 12)
down("d2", "fetch", 12, H, "ใช่")
down("fetch", "cls", H, H)
down("cls", "alert", H, H)
down("alert", "d3", H, 12)
down("d3", "summ", 12, H, "ใช่")
down("summ", "adj", H, 14)
down("adj", "save", 14, 12)
down("save", "send", 12, H)
down("send", "end", H, 7)

# D1 no -> left stop
box(LX, Y["d1"], LW, 12, "ตอบกลับให้ผู้ใช้\nตั้งค่าโปรไฟล์ให้ครบ\nก่อนสแกน แล้วสิ้นสุด", col=C_STOP, fs=8)
arrow([(MX - 17, Y["d1"]), (LX + LW / 2, Y["d1"])], "ไม่ใช่", ((MX - 17 + LX + LW / 2) / 2, Y["d1"] + 2.4))

# D2 no -> unmatched -> D3
box(LX, Y["d2"], LW, 11, "เก็บไว้ในรายการ\nที่จับคู่ไม่ได้\n(unmatched)", col=C_STOP, fs=8)
arrow([(MX - 17, Y["d2"]), (LX + LW / 2, Y["d2"])], "ไม่ใช่", ((MX - 17 + LX + LW / 2) / 2, Y["d2"] + 2.4))
arrow([(LX + LW / 2, Y["d2"] - 3), (31, Y["d2"] - 3), (31, Y["d3"]), (MX - 17, Y["d3"])])

# D3 no -> loop back
arrow([(MX + 17, Y["d3"]), (LOOPX, Y["d3"]), (LOOPX, Y["loop"]), (MX + MW / 2, Y["loop"])],
      "ไม่ใช่ (รายการถัดไป)", (LOOPX - 1, Y["d3"] + 2.6))

# ---------------- notes ----------------
note(LX, Y["cond"] - 6, LW, 22,
     "การแปลงโปรไฟล์ → risk_type\n"
     "• ตั้งครรภ์ → pregnancy\n"
     "• ผิวเป็นสิวง่าย → comedogenic,\n   acne_trigger\n"
     "• สิวเชื้อรา → fungal_acne_trigger\n"
     "• ผิวแพ้ง่าย (Sensitive) →\n   skin_sensitization, irritation", fs=7.1)
arrow([(LX + LW / 2, Y["cond"]), (MX - MW / 2, Y["cond"])], dashed=True, color="#888888", head=False)

note(LX, Y["cls"] - 6, LW - 1, 34,
     "สถานะรายส่วนผสม (ตามลำดับ)\n"
     "1 caution_with_risk\n"
     "2 compatible_with_risk\n"
     "3 risk_only\n"
     "4 caution\n"
     "5 compatible\n"
     "6 other_risk_only\n"
     "7 evidence_only\n"
     "8 no_evidence", fs=7.3)

# ---------------- databases ----------------
cylinder(RX, 151, RW, 58, "PostgreSQL\n(ฐานข้อมูลความรู้)",
         "users / user_profiles\nskin_types\ningredients\n(+ identity mapping CSV)\n"
         "ingredient_skin_effects\ningredient_risks\ningredient_evidence")
DBL = RX - RW / 2
arrow([(DBL, Y["prof"]), (MX + MW / 2, Y["prof"])], dashed=True, color=C_DB[1])
arrow([(DBL, Y["find"]), (MX + MW / 2, Y["find"])], dashed=True, color=C_DB[1])
arrow([(RX, 151 - 29 - 2), (RX, Y["fetch"]), (MX + MW / 2, Y["fetch"])], dashed=True, color=C_DB[1])

cylinder(RX, Y["save"] + 2, RW, 24, "PostgreSQL\n(บันทึกผล)",
         "scans\nscan_results\nrecommendations", fs=7.8)
arrow([(MX + MW / 2, Y["save"]), (DBL, Y["save"])], dashed=True, color=C_DB[1])

# ---------------- legend ----------------
lx, ly = 3, -12
ax.plot([lx, lx + 7], [ly, ly], color="#333333", lw=1.1)
ax.text(lx + 8.5, ly, "ลำดับการทำงาน", fontsize=7.4, va="center")
ax.plot([lx, lx + 7], [ly - 4.5, ly - 4.5], color=C_DB[1], lw=1.1, ls=(0, (4, 2.5)))
ax.text(lx + 8.5, ly - 4.5, "อ่าน/เขียนฐานข้อมูล", fontsize=7.4, va="center")

out = sys.argv[1]
fig.savefig(out, dpi=300, facecolor="white")
print("saved", out)
