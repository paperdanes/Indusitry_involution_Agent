
DASHSCOPE_API_KEY = ""
# 北京地域（中国大陆）：https://dashscope.aliyuncs.com/compatible-mode/v1
# 新加坡地域（国际）：https://dashscope-intl.aliyuncs.com/compatible-mode/v1
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

# -----------------------------
# 全局 LLM 设置（用于UI界面中左侧栏设置选项）
# -----------------------------
LLM_KEYS = ("DASHSCOPE_API_KEY", "BASE_URL", "MODEL", "TEMPERATURE", "TOP_P",
            "MAX_TOKENS","EMBED_MODEL", "EMBED_DIM", "EMBED_BATCH",
            "RAG_STORE_DIR", "TOP_K", "OUTPUT_DIR")

BASE_URL_PRESETS = {
    "北京（中国大陆）": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "新加坡（国际）": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    "自定义": "__CUSTOM__",
}
EMBED_MODEL_PRESETS = ["text-embedding-v4", "__CUSTOM__"]
MODEL_PRESETS = ["qwen-turbo", "qwen-plus", "qwen-max", "__CUSTOM__"]

#内卷标签识别、测定中新能源车企选项
SCOMPANY_LIST = ["比亚迪", "特斯拉", "理想汽车", "蔚来", "小鹏","吉利", "长城", "上汽", "广汽", "长安",
            "奇瑞", "零跑", "极氪", "问界", "小米汽车"]

# 常用模型示例：qwen-turbo / qwen-plus / qwen-max
MODEL = "qwen-plus"

# 推理参数
TEMPERATURE = 0.2
TOP_P = 0.9
MAX_TOKENS = 4096

EMBED_MODEL = "text-embedding-v4"
EMBED_DIM = 1024  # v3/v4 支持 dimensions 参数；v4 默认也可不填，但建议固定维度便于索引一致
EMBED_BATCH = 10  # v4 文档给的最大行数是 10，

# RAG 切分参数（先用字符长度近似，后面可换 token-based）
CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
XLSX_MAX_SHEETS = 20
XLSX_MAX_ROWS_PER_SHEET = 5000
XLSX_MAX_COLS_PER_SHEET = 50
XLSX_INCLUDE_EMPTY_VALUES = False

RAG_STORE_DIR = "C:\Rag_store"
TOP_K = 10
OUTPUT_DIR = "C:\Industry_involution_agent_output"

#政策仿真部分容易出现格式生成错误，需多次迭代，此处设置迭代上限
MAX_RETRY = 5

