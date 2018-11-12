build:
	jekyll build
	cp _site/app.yaml .

prod:
	JEKYLL_ENV=production jekyll build
	cp _site/app.yaml .

clean:
	rm -rf _site

deploy:
	gcloud app deploy
