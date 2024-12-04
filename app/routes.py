from flask import Blueprint, render_template, request, jsonify
from app.services.search import search_speeches

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        search_term = request.form['search_term']
        # Call the search function and pass the user query
        results = search_speeches(search_term)

        # Return the results to the same template
        return render_template('index.html', results=results, search_term=search_term)

    # If GET request, just show the search form
    return render_template('index.html', results=None)

@main_blueprint.route('/about')
def about():
    return render_template('about.html')
