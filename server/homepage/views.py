from django.shortcuts import render
from django.http import HttpResponse
# Create your views here.



def get_home_page(request):
    params = {"website_title": "Loris Jautakas", "mathjax_provider": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"}
    return render(request, "home.html", params)

def get_project_page(request):
    params = {"website_title": "Projects", "mathjax_provider": "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"}
    return render(request, "projects.html",params)