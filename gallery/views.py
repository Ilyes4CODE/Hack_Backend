from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.shortcuts import get_object_or_404
from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from Auth.permissions import IsFarmer
from .models import Post, PostImage, Comment
from django.utils import timezone

class PostListView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Browse community disease posts",
        operation_description="Returns anonymized posts submitted by farmers. Filterable by crop, wilaya, and disease tag.",
        manual_parameters=[
            openapi.Parameter('crop', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False, enum=['wheat','tomato','olive','date_palm','potato','onion','pepper','watermelon','citrus','barley']),
            openapi.Parameter('wilaya', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('disease_tag', openapi.IN_QUERY, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: 'List of posts', 401: 'Unauthorized'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def get(self, request):
        qs = Post.objects.all().order_by('-created_at')
        crop = request.query_params.get('crop')
        wilaya = request.query_params.get('wilaya')
        disease_tag = request.query_params.get('disease_tag')

        if crop: qs = qs.filter(crop=crop)
        if wilaya: qs = qs.filter(wilaya__icontains=wilaya)
        if disease_tag: qs = qs.filter(disease_tag__icontains=disease_tag)

        data = []
        for p in qs:
            data.append({
                'id': str(p.id),
                'caption': p.caption,
                'crop': p.crop,
                'wilaya': p.wilaya,
                'disease_tag': p.disease_tag,
                'created_at': p.created_at,
                'images': [request.build_absolute_uri(img.image.url) for img in p.images.all()],
                'comments_count': p.comments.count(),
                'is_author': p.author.id == request.user.id
            })
        return Response(data, status=status.HTTP_200_OK)

class PostCreateView(APIView):
    permission_classes = [IsFarmer]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Submit a community post",
        operation_description="Farmer submits a post with multiple images, caption, crop, wilaya, and optional disease tag. Immediately visible to all farmers.",
        manual_parameters=[
            openapi.Parameter('images', openapi.IN_FORM, type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_FILE), required=True),
            openapi.Parameter('caption', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('crop', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('wilaya', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('disease_tag', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
        ],
        consumes=['multipart/form-data'],
        responses={201: 'Post created', 400: 'Validation error', 401: 'Unauthorized'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def post(self, request):
        caption = request.data.get('caption', '').strip()
        crop = request.data.get('crop', '').strip()
        wilaya = request.data.get('wilaya', '').strip()
        disease_tag = request.data.get('disease_tag', '').strip()
        images = request.FILES.getlist('images')

        valid_crops = [c[0] for c in Post.CROPS]
        if not crop or crop not in valid_crops:
            return Response({'error': f'Invalid crop. Must be one of: {", ".join(valid_crops)}'}, status=status.HTTP_400_BAD_REQUEST)
        if not wilaya:
            return Response({'error': 'Wilaya is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not images:
            return Response({'error': 'At least one image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        post = Post.objects.create(
            author=request.user,
            caption=caption,
            crop=crop,
            wilaya=wilaya,
            disease_tag=disease_tag
        )

        for idx, img in enumerate(images):
            PostImage.objects.create(post=post, image=img, order=idx)

        return Response({
            'message': 'Post published successfully.',
            'id': str(post.id)
        }, status=status.HTTP_201_CREATED)

class PostDetailView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Get post details with comments",
        responses={200: 'Post details', 404: 'Not found'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def get(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        comments = [
            {
                'id': str(c.id),
                'content': c.content,
                'created_at': c.created_at,
                'is_author': c.author.id == request.user.id
            }
            for c in post.comments.order_by('created_at')
        ]
        return Response({
            'id': str(post.id),
            'caption': post.caption,
            'crop': post.crop,
            'wilaya': post.wilaya,
            'disease_tag': post.disease_tag,
            'created_at': post.created_at,
            'images': [request.build_absolute_uri(img.image.url) for img in post.images.all()],
            'comments': comments,
            'is_author': post.author.id == request.user.id
        }, status=status.HTTP_200_OK)

class PostUpdateView(APIView):
    permission_classes = [IsFarmer]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_summary="Update post details (author only)",
        consumes=['multipart/form-data'],
        manual_parameters=[
            openapi.Parameter('caption', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('crop', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('wilaya', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
            openapi.Parameter('disease_tag', openapi.IN_FORM, type=openapi.TYPE_STRING, required=False),
        ],
        responses={200: 'Updated', 403: 'Forbidden', 404: 'Not found'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def patch(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author != request.user:
            return Response({'error': 'Only the author can edit this post.'}, status=status.HTTP_403_FORBIDDEN)

        for field in ['caption', 'crop', 'wilaya', 'disease_tag']:
            if field in request.data:
                setattr(post, field, request.data.get(field, '').strip())
        post.save()
        return Response({'message': 'Post updated successfully.'}, status=status.HTTP_200_OK)

class PostDeleteView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Delete post (author only)",
        responses={204: 'Deleted', 403: 'Forbidden', 404: 'Not found'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def delete(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        if post.author != request.user:
            return Response({'error': 'Only the author can delete this post.'}, status=status.HTTP_403_FORBIDDEN)
        
        # Clean up images from disk
        for img in post.images.all():
            img.image.delete(save=False)
        post.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class CommentCreateView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Add a comment to a post",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['content'],
            properties={
                'content': openapi.Schema(type=openapi.TYPE_STRING, example='This looks like early blight.')
            }
        ),
        responses={201: 'Comment added', 400: 'Validation error', 404: 'Not found'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def post(self, request, pk):
        post = get_object_or_404(Post, pk=pk)
        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Comment content is required.'}, status=status.HTTP_400_BAD_REQUEST)
        
        comment = Comment.objects.create(post=post, author=request.user, content=content)
        return Response({
            'message': 'Comment added.',
            'id': str(comment.id),
            'content': comment.content,
            'created_at': comment.created_at
        }, status=status.HTTP_201_CREATED)

class CommentDeleteView(APIView):
    permission_classes = [IsFarmer]

    @swagger_auto_schema(
        operation_summary="Delete own comment",
        responses={204: 'Deleted', 403: 'Forbidden', 404: 'Not found'},
        security=[{"Bearer": []}],
        tags=['Gallery']
    )
    def delete(self, request, pk, comment_pk):
        comment = get_object_or_404(Comment, pk=comment_pk, post__pk=pk)
        if comment.author != request.user:
            return Response({'error': 'Only the author can delete this comment.'}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)