# app/utils.py
# Use Agg backend (headless) so matplotlib does not open GUI windows or require Tk
import matplotlib
matplotlib.use("Agg")

import base64
from io import BytesIO
import matplotlib.pyplot as plt

def fig_to_base64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight")
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode("ascii")
    plt.close(fig)
    return "data:image/png;base64," + img_b64
