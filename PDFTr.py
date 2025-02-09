import fitz  # PyMuPDF
from docx import Document

def pdf_to_word(pdf_path, word_path):
    # 打开 PDF 文件
    pdf_document = fitz.open(pdf_path)
    # 创建一个新的 Word 文档
    word_document = Document()

    # 逐页读取 PDF 内容
    for page_num in range(pdf_document.page_count):
        page = pdf_document.load_page(page_num)
        text = page.get_text()
        
        # 将文本添加到 Word 文档
        word_document.add_paragraph(text)

    # 保存 Word 文档
    word_document.save(word_path)

# 使用示例
pdf_path = "example.pdf"  # PDF 文件路径
word_path = "example.docx"  # 要保存的 Word 文件路径
# pdf_to_word(pdf_path, word_path)

pdf_to_word("f:/GS-433-03.pdf", "f:/GS-433-0321.docx")