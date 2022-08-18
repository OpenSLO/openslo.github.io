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

## Creating a blog post 

Please follow while creating a new post on our blog:

1. Create a file with the name of the post 
```sh
hugo new posts/{post-name}.md
```
2. In path /content/posts you'll find your newly created file 
3. Please add in the front matter variable called `cover` with a value pointing to the cover image of your post. You can link an image or use one which should be placed in `/assets` directory. 
4. Write your post
5. If you finished your work change draft value to false

Example front matter for the post
```yaml
title: "Hello world!"
date: 2022-08-18T13:00:42+02:00
draft: false
cover: /images/openslo_logo.svg
```
5. Thanks for your contribution! 
