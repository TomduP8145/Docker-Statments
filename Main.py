import os
import subprocess
import tempfile
import pytesseract
from flask import Flask, request, render_template_string
import re  # For handling regex

class SingleOrganizer:
    def __init__(self):
        self.app = Flask(__name__)
        self.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        self.poppler_path = r'C:\Program Files\Release-24.08.0-0\poppler-24.08.0\Library\bin'
        self.uploads_dir = tempfile.mkdtemp()
        pytesseract.pytesseract.tesseract_cmd = self.pytesseract_cmd
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/', methods=['GET', 'POST'])
        def index():
            table_data = []
            error = ''

            if request.method == 'POST':
                pdf_files = [
                    request.files.get('pdf_file_1'),
                    request.files.get('pdf_file_2'),
                    request.files.get('pdf_file_3')
                ]

                if not all(self.is_valid_pdf(file) for file in pdf_files if file):
                    error = "Please upload valid PDF files."
                elif len([f for f in pdf_files if f]) > 3:
                    error = "Please upload a maximum of 3 PDF files."
                else:
                    for pdf_file in pdf_files:
                        if pdf_file:
                            pdf_path = os.path.join(self.uploads_dir, pdf_file.filename)
                            pdf_file.save(pdf_path)
                            extracted_text = self.extract_info_from_pdf(pdf_path)
                            if extracted_text:
                                table_data.extend(self.create_table_from_text(extracted_text))

            return render_template_string(self.html_template(), table_data=table_data, error=error)

    def html_template(self):
        return '''
        <!doctype html>
        <html lang="en">
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <title>PDF Info Extractor</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 0; background-color: #2c3e50; color: white; }
                .container { background-color: #34495e; padding: 20px; border-radius: 5px; text-align: center; }
                h1 { color: #fff; }
                table { width: 100%; border-collapse: collapse; margin-top: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f4f4f4; color: black; }
                .error { color: red; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>PDF Info Extractor</h1>
                <form method="post" enctype="multipart/form-data">
                    <label for="pdf_file_1">Upload PDF 1:</label>
                    <input type="file" name="pdf_file_1" required>
                    <label for="pdf_file_2">Upload PDF 2:</label>
                    <input type="file" name="pdf_file_2">
                    <label for="pdf_file_3">Upload PDF 3:</label>
                    <input type="file" name="pdf_file_3">
                    <button type="submit">Extract Info</button>
                </form>
                <div class="error">{{ error }}</div>
                {% if table_data %}
                    <table>
                        <tr>
                            <th>Date</th>
                            <th>Details</th>
                            <th>Amount</th>
                            <th>Interest Rate</th>
                            <th>Balance</th>
                        </tr>
                        {% for row in table_data %}
                            <tr>
                                <td>{{ row[0] }}</td>
                                <td>{{ row[1] }}</td>
                                <td>{{ row[2] }}</td>
                                <td>{{ row[3] }}</td>
                                <td>{{ row[4] }}</td>
                            </tr>
                        {% endfor %}
                    </table>
                {% endif %}
            </div>
        </body>
        </html>
        '''

    def is_valid_pdf(self, file):
        return file and file.filename.lower().endswith('.pdf')

    def extract_info_from_pdf(self, pdf_path):
        try:
            text = self.extract_text_from_pdf(pdf_path)
            return text
        except Exception as e:
            return f"Error processing file: {str(e)}"

    def extract_text_from_pdf(self, pdf_path):
        text = ''
        output_image_path = os.path.join(self.uploads_dir, 'page')

        command = [os.path.join(self.poppler_path, 'pdftoppm'), '-png', pdf_path, output_image_path]

        try:
            subprocess.run(command, check=True)
        except FileNotFoundError:
            return "Error: Poppler (pdftoppm) is not found. Ensure the path is correct."
        except Exception as e:
            return f"Error running pdftoppm: {str(e)}"

        for i in range(len(os.listdir(self.uploads_dir))):
            image_path = f"{output_image_path}-{i + 1}.png"
            if os.path.exists(image_path):
                text += pytesseract.image_to_string(image_path) + '\n'

        return text.strip()

    def create_table_from_text(self, text):
        rows = text.split('\n')
        table_data = []

        for row in rows:
            if row.strip():
                columns = self.extract_columns(row)
                if len(columns) == 5:  # Ensure we have exactly 5 columns (Date, Details, Amount, Interest Rate, Balance)
                    table_data.append(columns)

        return table_data

    def extract_columns(self, row):
        # Use regex to extract the five required fields
        match = re.match(r'(\d{8})\s+([A-Z\s]+)\s+([0-9,.-]+)\s+([0-9.]+)\s+([0-9,.-]+)', row)

        if match:
            date = match.group(1)
            details = match.group(2).strip()
            amount = match.group(3).replace(',', '')  # Remove commas from numbers
            interest_rate = match.group(4)
            balance = match.group(5).replace(',', '')

            return [date, details, amount, interest_rate, balance]
        return [''] * 5  # Return empty values if the row does not match expected format

    def run(self):
        self.app.run(debug=True)


if __name__ == '__main__':
    organizer = SingleOrganizer()
    organizer.run()
