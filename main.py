from flask import Flask, render_template, redirect, request
from binance_average_buy import *

app = Flask(__name__)

headings = ('Name', 'Average buy', 'Amount')
data = []

@app.route('/')
def index():
    return render_template('index.html', headings=headings, data=data)


@app.route('/result')
def result():
    global data
    data = main()
    return redirect('http://127.0.0.1:5000/')


if __name__ == '__main__':
    app.run(debug=True)
