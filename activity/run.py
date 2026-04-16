from fitness_app1 import create_app
 
app = create_app()
 
if __name__ == '__main__':
    #debug mode so errors show up
    app.run(debug=True)