# The OpenSLO homepage source code

Everything that has been committed to the `main` branch is published automatically to [openslo.com](https://openslo.com/).

The website is built with [HUGO](https://gohugo.io/). To run it locally execute

```sh
hugo server
```

to update it just create a PR and merge it to the `main` branch.

This website contains a blog section, everybody interested in SLO, SRE, OpenSLO, etc. is welcome to write articles.
The flow is the same as for regular contributions, review will be made in a PR.

For something more complicated or when you are in doubt please create an issue first to gather feedback.

## Creating blog post 

Please follow while creating new post on our blog:

1. Create file with name of post 
```sh
hugo new posts/{post-name}.md
```
2. In path /content/posts you'll find your newly created file 
3. Please add in front matter variable called `cover` with value pointing to cover image of your post. You can link image or use one which should be placed in /assets directory. 
4. Fill post with content
5. If you finished your work change draft value to false
5. Thanks for your contribution! 
