# -*- coding: UTF-8 -*-
from flask import render_template,redirect,url_for,session,flash,request,current_app,request,jsonify
from ..decorators import admin_required,permission_required
from . import trade
from .. import db
from flask.ext.login import login_required,current_user
from ..models import Permission,User,Role,Post,Comment,getPrimaryKeyId
from forms import PostForm,CommentForm, SearchForm , deleteForm
from json import loads


@trade.route('/trade_list')
def trade_list():
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, per_page=current_app.config['JXNUGO_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    return render_template('trade/trade_list.html',posts=posts,pagination=pagination)


@trade.route('/trade_post',methods=['POST', 'GET'])
@login_required
def trade_post():
    form = PostForm()
    if form.validate_on_submit():
        recv = form.img.data
        s = loads(recv)
        l = []
        for x in s['photos']:
            temp = x['key']
            l.append(temp)
        photo = ":".join(l)
        post = Post(id=getPrimaryKeyId('isPost'), body=form.body.data, goodName=form.name.data, goodPrice=form.price.data,
                  goodNum=form.num.data, goodLocation=form.location.data, goodQuality=form.quality.data,
                  goodTag=form.tag.data, contact=form.mycontact.data, goodBuyTime=form.buyTime.data,  photos=photo, author_id=current_user.id)
        db.session.add(post)
        db.session.commit()
        flash(u'帖子发布成功')
        return redirect(url_for('trade.trade_list'))  # 感觉 返回列表会好一些
    return render_template('trade/trade_post.html', form=form)


@trade.route('/trade_detail/<goodId>', methods=['GET', 'POST'])
def trade_detail(goodId):
    post = Post.query.get_or_404(goodId)
    form = CommentForm()
    if form.validate_on_submit():
        if current_user.is_anonymous:
            flash(u'请登录后再尝试评论帖子')
            return redirect(url_for('auth.passport'))
        else:
            comment = Comment(body=form.body.data, post=post,
            author = current_user._get_current_object())
            db.session.add(comment)
            db.session.commit()
            flash(u'你的评论已提交.')
            return redirect(url_for('.trade_detail', goodId=post.id, page=-1))
    page = request.args.get('page', 1, type=int)
    if page == -1:
        page = (post.comments.count() - 1) // \
            current_app.config['JXNUGO_COMMENTS_PER_PAGE'] + 1
    pagination = post.comments.order_by(Comment.timestamp.asc()).paginate(
        page, per_page=current_app.config['JXNUGO_COMMENTS_PER_PAGE'],
        error_out=False)
    comments = pagination.items
    author = current_user._get_current_object()
    return render_template('trade/trade_detail.html', post=post, form=form,
                           comments=comments, pagination=pagination,user=author)


@trade.route('/collect/<pid>',methods=['GET'])
@login_required
def collect(pid):
    post = Post.query.filter_by(id=pid).first()
    if post is None:
        flash(u'该帖子不存在')
    if current_user.is_collecting(post):
        flash(u'已经收藏了这篇帖子,无需再次收藏')
        return redirect(url_for('.trade_detail',goodId=pid))
    current_user.collect(post)
    flash(u'收藏成功')
    return redirect(url_for('.trade_detail',goodId=pid))


@trade.route('/uncollect/<pid>', methods=['GET'])
@login_required
def uncollect(pid):
    post = Post.query.filter_by(id=pid).first()
    if post is None:
        flash(u'该帖子不存在')
    current_user.uncollect(post)
    flash(u'成功取消收藏')
    return redirect(url_for('.trade_detail',goodId=pid))


@trade.route('/moderate')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate():
    page = request.args.get('page',1,type=int)
    pagination = Comment.query.order_by(Comment.timestamp.desc()).paginate(
        page, per_page=current_app.config['JXNUGO_COMMENT_PER_PAGE'],
        error_out=False
    )
    comments = pagination.items
    return render_template('trade/moderate.html', comments=comments, pagination=pagination, page=page)


@trade.route('/moderate/enable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_enable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = False
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)), )


@trade.route('/moderate/disable/<int:id>')
@login_required
@permission_required(Permission.MODERATE_COMMENTS)
def moderate_disable(id):
    comment = Comment.query.get_or_404(id)
    comment.disabled = True
    db.session.add(comment)
    return redirect(url_for('.moderate',
                            page=request.args.get('page', 1, type=int)), )


@trade.route('/query_post/<problem>')
def query_post(problem):
    queryname = problem
    print queryname
    if queryname == '':
        flash('请输入关键字后再进行查询操作')
        return redirect(url_for('.trade_list'))
    else:
        page = request.args.get('page', 1, type=int)
        pagination = Post.query.filter(Post.goodName.like('%'+queryname+'%')).paginate(
            page, per_page=current_app.config['JXNUGO_POSTS_PER_PAGE'],
            error_out=False
        )
    
        posts = pagination.items
        return render_template('trade/query_posts.html', posts=posts, pagination=pagination,problem=problem)


@trade.route('/post_category/<posttag>')
def post_category(posttag):
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.filter_by(goodTag=posttag).paginate(
        page, per_page=current_app.config['JXNUGO_POSTS_PER_PAGE'],
        error_out=False
    )
    posts = pagination.items
    return render_template('trade/trade_list.html', posts=posts, pagination=pagination)


@trade.route('/post_delete', methods=['GET', 'POST'])
@login_required
@admin_required
def post_delete():
    delete_postid = deleteForm()
    if delete_postid.validate_on_submit():
        pid = delete_postid.pid.data
        p = Post.query.filter_by(id=pid).first()
        if p is None:
            flash(u'该帖子不存在')
        else:
            comments = Comment.query.filter_by(post_id=p.id).all()  # 删除评论
            for comment in comments:
                db.session.delete(comment)
            all_user = User.query.all()     # 删除收藏的关系
            for user in all_user:
                if p in user.collectionPost.all():
                    user.collectionPost.remove(p)
                else:
                    pass
            db.session.delete(p)
            db.session.commit()
            flash(u'帖子及其评论删除成功')
    return render_template('trade/post_delete.html', form=delete_postid)


@trade.route('/delete_self_post/<int:pid>')
@login_required
def delete_self_post(pid):
    p = Post.query.filter_by(id=pid).first()
    if p is None:
        flash(u'该帖子不存在')
    else:
        comments = Comment.query.filter_by(post_id=p.id).all()  # 删除评论
        for comment in comments:
            db.session.delete(comment)
        all_user = User.query.all()     # 删除收藏的关系
        for user in all_user:
            if p in user.collectionPost.all():
                user.collectionPost.remove(p)
            else:
                pass
        db.session.delete(p)
        db.session.commit()
        flash(u'帖子及其评论删除成功')
    return redirect(url_for('trade.trade_list'))
