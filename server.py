from flask import Flask, render_template, request, redirect, url_for, session
# from flask import flash
import client_manager as client
import service_user as usr
import service_question as qst
import service_answer as ans
import service_comment as com
import service_tag as tag
import data_manager

from os import environ
from functools import wraps

import util
from data_manager import add_new_entry

app = Flask(__name__)
PATH = app.root_path

app.config['SECRET_KEY'] = environ.get('SECRET_KEY')


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if client.get_logged_user_id() is None:
            return render_template("login.html", message="You have to be logged in to perform this action.")
        return f(*args, **kwargs)
    return decorated_function


#
#          ------>> DISPLAY AND INSERTING <<------
#

@app.route("/")
def get_five_question():
    """Services redirection to main page with loaded list of the 5 latest questions."""
    questions = qst.get_five_questions()
    return render_template('list.html', questions=questions, sorted=False)


@app.route("/list")
def get_list_of_questions():
    """Services redirection to main page with loaded list of all questions."""
    if len(request.args) == 0:
        questions = qst.get_all_data()
    else:
        questions = qst.get_all_data_by_query(request.args.get('order_by'),
                                              request.args.get('order_direction'))

    return render_template('list.html', questions=questions, sorted=True)


@app.route("/search")
def get_entries_by_search_phrase():
    search_phrase = request.args.get('q')

    questions, questions_with_answers = qst.get_entries_by_search_phrase(search_phrase)
    highlighted_questions_id = [question['id'] for question in questions_with_answers]
    return render_template("list.html",
                           searched=True,
                           questions=questions + questions_with_answers,
                           questions_id_with_highlighted_answers=highlighted_questions_id)


@app.route("/question/<question_id>")
def display_question(question_id):
    """Services redirection to specific question page."""

    qst.update_views_count(question_id)

    question = qst.get_question_by_id(question_id)
    answers = ans.get_answers_for_question(question_id)
    tags = qst.get_tags_for_question(question_id)
    comments = qst.get_comments_for_question(question_id)
    question_to_render = []
    answers_to_render = {}

    if client.get_logged_user_id():
        answer_ids = [answer['id'] for answer in answers]
        question_to_render, answers_to_render = client.get_voted_posts_to_render(question['id'], answer_ids)

    return render_template("question.html",
                           question=question,
                           answers=answers,
                           tags=tags,
                           comments=comments,
                           question_to_render=question_to_render,
                           answers_to_render=answers_to_render
                           )


@app.route("/add-question")
@login_required
def display_add_question():
    """Services redirection to displaying interface of adding question"""
    # if session.get('logged_user', None):
    return render_template("add_question.html")
    # else:
    #     return render_template("login.html", message="You have to be logged in to add questions or answers")



@app.route("/add-question", methods=['POST'])
@login_required
def add_question():
    """Services posting question."""
    question_id = data_manager.add_new_entry(
        table_name='question',
        form_data=request.form,
        request_files=request.files,
        user_id=client.get_logged_user_id()
        )

    # add_user_question_activity(session['user_id'], question_id)

    return redirect(url_for('display_question', question_id=question_id))


@app.route("/question/<question_id>/add-answer")
@login_required
def display_add_answer(question_id):
    """Services redirection to displaying interface of adding answer."""
    # if session.get('logged_user', None):
    return render_template("add_answer.html")
    # else:
    #     return render_template("login.html", message="You have to be logged in to add questions or answers")


@app.route("/question/<question_id>/add-answer", methods=["POST"])
@login_required
def new_answer(question_id):
    """Services posting answer."""

    answer_id = add_new_entry(
        table_name='answer',
        form_data=request.form,
        request_files=request.files,
        question_id=question_id,
        user_id=client.get_logged_user_id())

    # add_user_answer_activity(session['user_id'], answer_id)

    return redirect(f'/question/{question_id}')


@app.route("/answer/<answer_id>/add-comment")
@login_required
def add_answer_comment(answer_id):
    return render_template('add_answer_comment.html', answer_id=answer_id)


@app.route("/answer/<answer_id>/add-comment", methods=['POST'])
@login_required
def post_answer_comment(answer_id):
    message = request.form['message']
    com.add_comment(message, 'answer', answer_id, client.get_logged_user_id())
    redirection_id = util.get_question_id_from_entry('answer', answer_id)

    return redirect(url_for('display_question', question_id=redirection_id))


@app.route("/question/<question_id>/add-comment")
@login_required
def display_add_comment(question_id):
    return render_template('add_comment.html')


@app.route("/question/<question_id>/add-comment", methods=["POST"])
@login_required
def post_question_comment(question_id):
    com.add_comment(request.form['message'], 'question', question_id, client.get_logged_user_id())
    return redirect(f'/question/{question_id}')


@app.route("/question/<question_id>/new-tag")
@login_required
def display_new_tag(question_id):
    all_tags = tag.get_all_tags()
    return render_template('new_tag.html',
                           question_id=question_id,
                           all_tags=all_tags
                           )


@app.route("/question/<question_id>/new-tag", methods=['POST'])
@login_required
def add_new_tag(question_id):
    tag.add_new_tag_to_db(request.form['tag'])
    return redirect(url_for('display_new_tag', question_id=question_id))


@app.route("/question/<question_id>/new-tag-question", methods=['POST'])
@login_required
def add_new_tag_to_question(question_id):
    print(request.form['tag_id'])
    message = tag.add_new_tag_to_question(question_id, request.form['tag_id'])
    return redirect(url_for('display_question', question_id=question_id))


#
#          ------>> DELETIONS <<------
#


@app.route("/question/<question_id>/delete")
@login_required
def delete_question(question_id):
    if client.get_post_if_permitted(question_id, 'question'):
        qst.delete_question(question_id)
        return redirect('/')
    else:
        return render_template("login.html", message="You don't have permission to perform this action")



@app.route("/question/<question_id>/tag/<tag_id>/delete")
@login_required
def delete_single_tag_from_question(question_id, tag_id):
    if client.get_post_if_permitted(question_id, 'question'):
        tag.remove_single_tag_from_question(question_id, tag_id)
        return redirect(url_for('display_question', question_id=question_id))
    else:
        return render_template("login.html", message="You don't have permission to perform this action")



@app.route("/answer/<answer_id>/delete")
@login_required
def delete_answer(answer_id):
    """Services deleting answer."""
    if client.get_post_if_permitted(answer_id, 'answer'):
        redirection_id = util.get_question_id_from_entry('answer', answer_id)
        ans.delete_answer_by_id(answer_id)
        return redirect(url_for('display_question', question_id=redirection_id))
    else:
        return render_template("login.html", message="You don't have permission to perform this action")


@app.route("/comment/<comment_id>/delete")
@login_required
def delete_comment(comment_id):
    if client.get_post_if_permitted(comment_id, 'comment'):
        redirection_id = util.get_question_id_from_entry('comment', comment_id)
        com.delete_comment_by_id(comment_id)
        return redirect(url_for('display_question', question_id=redirection_id))
    else:
        return render_template("login.html", message="You don't have permission to perform this action")

#
#          ------>> EDITIONS <<------
#


@app.route("/question/<question_id>/edit")
@login_required
def edit_question(question_id):
    """Services displaying edition of question and posting edited version."""
    if client.get_post_if_permitted(question_id, 'question'):
        question = qst.get_single_question(question_id)
        return render_template('edit_question.html', question_id=question_id, question=question)
    else:
        return render_template("login.html", message="You don't have permission to perform this action")


@app.route("/question/<question_id>/edit", methods=['POST'])
@login_required
def save_edited_question(question_id):
    title = request.form['title']
    message = request.form['message']

    qst.save_edited_question(question_id, title, message)

    return redirect(url_for('display_question', question_id=question_id))


@app.route("/answer/<answer_id>/edit")
@login_required
def display_answer_to_edit(answer_id):
    """Services displaying edition of answer and posting edited version."""
    if client.get_post_if_permitted(answer_id, 'answer'):
        answer = ans.get_answer(answer_id)
        return render_template('edit_answer.html', answer_id=answer_id, answer=answer)
    else:
        return render_template("login.html", message="You don't have permission to perform this action")



@app.route("/answer/<answer_id>/edit", methods=['POST'])
@login_required
def save_edited_answer(answer_id):
    ans.save_edited_answer(answer_id, request.form['message'])
    redirection_id = util.get_question_id_from_entry('answer', answer_id)

    return redirect(url_for('display_question', question_id=redirection_id))


@app.route("/<entry_type>/<entry_id>/<vote_value>", methods=["POST"])
@login_required
def vote_on_post(entry_id, vote_value, entry_type):
    """Services voting on questions and answers"""
    # if client.get_post_if_permitted(entry_id, entry_type):
    client.process_voting(entry_id, vote_value, entry_type)
    redirection_id = util.get_question_id_from_entry(entry_type, entry_id)

    if entry_type == 'answer':
        usr.add_user_answer_activity(client.get_logged_user_id(), entry_id)
    else:
        usr.add_user_question_activity(client.get_logged_user_id(), entry_id)

    return redirect(url_for('display_question', question_id=redirection_id))
    # else:
    #     return render_template("login.html", message="You don't have permission to perform this action")


@app.route("/comment/<comment_id>/edit")
@login_required
def display_comment_edit(comment_id):
    if client.get_post_if_permitted(comment_id, 'comment'):
        comment = com.get_comment_by_id(comment_id)
        return render_template('edit_comment.html',
                               message=comment['message'],
                               comment_id=comment_id)
    else:
        return render_template("login.html", message="You don't have permission to perform this action")


@app.route("/comment/<comment_id>/edit", methods=["POST"])
@login_required
def edit_comment(comment_id):
    new_message = request.form['message']
    com.update_comment(comment_id, new_message)

    redirection_id = util.get_question_id_from_entry('comment', comment_id)

    return redirect(url_for('display_question', question_id=redirection_id))


@app.route('/login')
def login():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def post_login():
    login = request.form['login']
    password = request.form['password']

    if usr.is_authenticated(login, password):
        user = usr.get_users_session_data(login)
        client.set_session(user['login'], user['id'])

        return redirect(url_for('get_five_question'))

    return render_template('login.html', message="Incorrect Login or Password")


@app.route('/logout')
def logout():
    client.drop_session()
    return redirect(url_for('get_five_question'))


@app.route('/registration')
def display_registration():
    return render_template('registration.html')


@app.route('/registration', methods=['POST'])
def registration():
    login = request.form.get('login')
    password = request.form.get('password')

    response = client.process_registration(login, password)

    if response:
        return render_template('registration.html', message=response)
    else:
        return render_template('login.html', registration_message="You've been registered")


@app.route('/users')
@login_required
def users():
    # if session.get('logged_user', None):
    users = usr.get_users()
    return render_template("users.html", users=users)
    # else:
    #     return render_template("login.html", message="You have to be logged in to see users")


@app.route('/user/<user_id>')
@login_required
def user_page(user_id):
    # if session.get('logged_user', None):
    user = usr.get_user_data(user_id)
    questions = usr.get_questions_of_user(user_id)
    answers = usr.get_answers_of_user(user_id)
    comments = usr.get_comments_of_user(user_id)
    return render_template("user_page.html",
                           user=user,
                           questions=questions,
                           answers=answers,
                           comments=comments)
    # else:
    #     return render_template("login.html", message="You have to be logged in to see users")

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == "__main__":
    app.run(
        host='127.0.0.1',
        port=5050,
        debug=True)

