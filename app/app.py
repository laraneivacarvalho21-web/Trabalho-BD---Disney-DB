import warnings
warnings.filterwarnings('ignore', category=FutureWarning)
from flask import abort, render_template, Flask, request, session, redirect, url_for, send_file
import logging
import db
import secrets
import logging

"""
Disney+ Catalog Application (Group 51)
======================================
Authors: 
- Alice de Azevedo Silva
- Lara Neiva Carvalho
- Ana Sofia Pinto Santos

Description:
Main Flask application handling routing, view logic, and SQL query execution.
"""

LOG = logging.getLogger(__name__)

APP = Flask(__name__)
APP.secret_key = secrets.token_hex(16)  # Secret key for session management

# Initialize database with Flask app
db.init_app(APP)

# Inject 'current_theme' into all templates context
@APP.context_processor
def inject_theme():
    return {'current_theme': session.get('theme', 'disney')}

# ============================================
# THEME TOGGLE
# ============================================

@APP.route('/toggle-theme')
def toggle_theme():
    """
    Toggles the CSS theme between 'disney' (default) and 'christmas'.
    Stores the preference in the user session.
    """
    current_theme = session.get('theme', 'disney')
    new_theme = 'christmas' if current_theme == 'disney' else 'disney'
    session['theme'] = new_theme
    return redirect(request.referrer or url_for('index'))

# ============================================
# HOME PAGE
# ============================================

@APP.route('/')
def index():
    """
    Home page rendering global statistics via scalar subqueries.
    Efficiently counts rows across all major tables.
    """
    stats = {}
    stats = db.execute('''
        SELECT 
          (SELECT COUNT(*) FROM Content) as total_content,
          (SELECT COUNT(*) FROM Content WHERE type='Movie') as total_movies,
          (SELECT COUNT(*) FROM Content WHERE type='TV Show') as total_shows,
          (SELECT COUNT(*) FROM Participant) as total_participants,
          (SELECT COUNT(DISTINCT participant_id) FROM Directs) as total_directors,
          (SELECT COUNT(DISTINCT participant_id) FROM Acts_In) as total_actors,
          (SELECT COUNT(*) FROM Country) as total_countries,
          (SELECT COUNT(*) FROM Genre) as total_genres
    ''').fetchone()
    logging.info(stats)
    return render_template('index.html', stats=stats)

@APP.route('/download-db')
def download_db():
    """Route to download the SQLite database file"""
    try:
        # 'as_attachment=True' forces the browser to download instead of displaying
        return send_file('disney.db', as_attachment=True, download_name='disney.db')
    except Exception as e:
        return str(e), 404


# ============================================
# CONTENT ENDPOINTS
# ============================================

@APP.route('/content/')
def list_content():
    """Fetches all content ordered by title."""
    contents = db.execute('''
        SELECT show_id, type, title, release_year, rating, duration 
        FROM Content
        ORDER BY title
    ''').fetchall()
    return render_template('content-list.html', contents=contents)


@APP.route('/content/<show_id>/')
def get_content(show_id):
    """
    Detailed view for a single Movie/TV Show.
    Performs multiple JOIN queries to fetch related Entities (M:N relationships):
    - Directors
    - Actors (Limited to 20 for display performance)
    - Countries
    - Genres
    """
    content = db.execute('''
        SELECT * FROM Content WHERE show_id = ?
    ''', [show_id]).fetchone()
    
    if content is None:
        abort(404, f'Content {show_id} not found.')
    
    directors = db.execute('''
        SELECT p.name 
        FROM Participant p
        JOIN Directs d ON p.participant_id = d.participant_id
        WHERE d.show_id = ?
    ''', [show_id]).fetchall()
    
    actors = db.execute('''
        SELECT p.name 
        FROM Participant p
        JOIN Acts_In a ON p.participant_id = a.participant_id
        WHERE a.show_id = ?
        LIMIT 20
    ''', [show_id]).fetchall()
    
    countries = db.execute('''
        SELECT c.name 
        FROM Country c
        JOIN Produced_In ai ON c.country_id = ai.country_id
        WHERE ai.show_id = ?
    ''', [show_id]).fetchall()
    
    genres = db.execute('''
        SELECT g.name 
        FROM Genre g
        JOIN Belongs_To bt ON g.genre_id = bt.genre_id
        WHERE bt.show_id = ?
    ''', [show_id]).fetchall()
    
    return render_template('content-detail.html', 
                         content=content,
                         directors=directors,
                         actors=actors,
                         countries=countries,
                         genres=genres)


# ============================================
# PARTICIPANT ENDPOINTS
# ============================================

@APP.route('/participant/')
def list_participants():
    """Lists all participants with dynamic counts of their roles."""
    participants = db.execute('''
        SELECT p.participant_id, p.name,
               (SELECT COUNT(*) FROM Acts_In WHERE Acts_In.participant_id = p.participant_id) as actor_count,
               (SELECT COUNT(*) FROM Directs WHERE Directs.participant_id = p.participant_id) as director_count
        FROM Participant p
        ORDER BY p.name
    ''').fetchall()
    return render_template('participant-list.html', participants=participants)


@APP.route('/participant/<int:participant_id>/')
def get_participant(participant_id):
    """Shows participant profile and their filmography separated by role."""
    participant = db.execute('''
        SELECT * FROM Participant WHERE participant_id = ?
    ''', [participant_id]).fetchone()
    
    if participant is None:
        abort(404, f'Participant {participant_id} not found.')
    
    # Fetch works where they acted
    actor_contents = db.execute('''
        SELECT c.show_id, c.title, c.type, c.release_year
        FROM Content c
        JOIN Acts_In ai ON c.show_id = ai.show_id
        WHERE ai.participant_id = ?
        ORDER BY c.release_year DESC
    ''', [participant_id]).fetchall()
    
    # Fetch works where they directed
    director_contents = db.execute('''
        SELECT c.show_id, c.title, c.type, c.release_year
        FROM Content c
        JOIN Directs d ON c.show_id = d.show_id
        WHERE d.participant_id = ?
        ORDER BY c.release_year DESC
    ''', [participant_id]).fetchall()
    
    return render_template('participant-detail.html', 
                         participant=participant, 
                         actor_contents=actor_contents,
                         director_contents=director_contents)


# ============================================
# COUNTRY ENDPOINTS
# ============================================

@APP.route('/country/')
def list_countries():
    """Lists countries and count of titles produced in each."""
    countries = db.execute('''
        SELECT country_id, name,
               (SELECT COUNT(*) FROM Produced_In 
                WHERE Produced_In.country_id = Country.country_id) as content_count
        FROM Country
        ORDER BY name
    ''').fetchall()
    return render_template('country-list.html', countries=countries)


@APP.route('/country/<int:country_id>/')
def get_country(country_id):
    """Filters catalog by country availability."""
    country = db.execute('''
        SELECT * FROM Country WHERE country_id = ?
    ''', [country_id]).fetchone()
    
    if country is None:
        abort(404, f'Country {country_id} not found.')
    
    contents = db.execute('''
        SELECT c.show_id, c.title, c.type, c.release_year
        FROM Content c
        JOIN Produced_In ai ON c.show_id = ai.show_id
        WHERE ai.country_id = ?
        ORDER BY c.title
    ''', [country_id]).fetchall()
    
    return render_template('country-detail.html', 
                         country=country, 
                         contents=contents)


# ============================================
# GENRE ENDPOINTS
# ============================================

@APP.route('/genre/')
def list_genres():
    """Lists genres and count of titles in each."""
    genres = db.execute('''
        SELECT genre_id, name,
               (SELECT COUNT(*) FROM Belongs_To 
                WHERE Belongs_To.genre_id = Genre.genre_id) as content_count
        FROM Genre
        ORDER BY name
    ''').fetchall()
    return render_template('genre-list.html', genres=genres)


@APP.route('/genre/<int:genre_id>/')
def get_genre(genre_id):
    """Filters catalog by genre/category."""
    genre = db.execute('''
        SELECT * FROM Genre WHERE genre_id = ?
    ''', [genre_id]).fetchone()
    
    if genre is None:
        abort(404, f'Genre {genre_id} not found.')
    
    contents = db.execute('''
        SELECT c.show_id, c.title, c.type, c.release_year
        FROM Content c
        JOIN Belongs_To bt ON c.show_id = bt.show_id
        WHERE bt.genre_id = ?
        ORDER BY c.title
    ''', [genre_id]).fetchall()
    
    return render_template('genre-detail.html', 
                         genre=genre, 
                         contents=contents)

# ============================================
# TABELA: ACTS_IN (Relação N:M)
# ============================================

@APP.route('/acts_in/')
def list_acts_in():
    """Lista todas as relações de atuação (Tabela Acts_In)"""
    # Fazemos JOIN para mostrar os Nomes e Títulos em vez de apenas IDs numéricos
    acts = db.execute('''
        SELECT ai.show_id, ai.participant_id, c.title, p.name
        FROM Acts_In ai
        JOIN Content c ON ai.show_id = c.show_id
        JOIN Participant p ON ai.participant_id = p.participant_id
        LIMIT 100 -- Limitado para não crashar o browser se forem milhares
    ''').fetchall()
    return render_template('relationship-list.html', 
                           title="Tabela: Acts_In", 
                           items=acts, 
                           type='acts_in')

@APP.route('/acts_in/<show_id>/<int:participant_id>/')
def get_acts_in(show_id, participant_id):
    """Detalhe de uma linha específica da tabela Acts_In"""
    relation = db.execute('''
        SELECT c.title, p.name, c.show_id, p.participant_id
        FROM Acts_In ai
        JOIN Content c ON ai.show_id = c.show_id
        JOIN Participant p ON ai.participant_id = p.participant_id
        WHERE ai.show_id = ? AND ai.participant_id = ?
    ''', [show_id, participant_id]).fetchone()

    if relation is None:
        abort(404, 'Relação não encontrada')

    return render_template('relationship-detail.html', 
                           title="Detalhe Acts_In", 
                           data=relation, 
                           type='acts_in')

# ============================================
# TABELA: BELONGS_TO (Relação N:M)
# ============================================

@APP.route('/belongs_to/')
def list_belongs_to():
    relationships = db.execute('''
        SELECT bt.show_id, bt.genre_id, c.title, g.name
        FROM Belongs_To bt
        JOIN Content c ON bt.show_id = c.show_id
        JOIN Genre g ON bt.genre_id = g.genre_id
        LIMIT 100
    ''').fetchall()
    return render_template('relationship-list.html', 
                           title="Tabela: Belongs_To", 
                           items=relationships, 
                           type='belongs_to')

@APP.route('/belongs_to/<show_id>/<int:genre_id>/')
def get_belongs_to(show_id, genre_id):
    relation = db.execute('''
        SELECT c.title, g.name, c.show_id, g.genre_id
        FROM Belongs_To bt
        JOIN Content c ON bt.show_id = c.show_id
        JOIN Genre g ON bt.genre_id = g.genre_id
        WHERE bt.show_id = ? AND bt.genre_id = ?
    ''', [show_id, genre_id]).fetchone()
    
    if relation is None: 
        abort(404)
        
    return render_template('relationship-detail.html', 
                           title="Detalhe Belongs_To", 
                           data=relation, 
                           type='belongs_to')

# ============================================
# TABELA: DIRECTS (Relação N:M)
# ============================================

@APP.route('/directs/')
def list_directs():
    """Lista todas as relações de realização (Tabela Directs)"""
    directs = db.execute('''
        SELECT d.show_id, d.participant_id, c.title, p.name
        FROM Directs d
        JOIN Content c ON d.show_id = c.show_id
        JOIN Participant p ON d.participant_id = p.participant_id
        LIMIT 100
    ''').fetchall()
    return render_template('relationship-list.html', 
                           title="Tabela: Directs (Realiza)", 
                           items=directs, 
                           type='directs')

@APP.route('/directs/<show_id>/<int:participant_id>/')
def get_directs(show_id, participant_id):
    """Detalhe de uma linha específica da tabela Directs"""
    relation = db.execute('''
        SELECT c.title, p.name, c.show_id, p.participant_id
        FROM Directs d
        JOIN Content c ON d.show_id = c.show_id
        JOIN Participant p ON d.participant_id = p.participant_id
        WHERE d.show_id = ? AND d.participant_id = ?
    ''', [show_id, participant_id]).fetchone()

    if relation is None:
        abort(404, 'Relação Directs não encontrada')

    return render_template('relationship-detail.html', 
                           title="Detalhe Directs", 
                           data=relation, 
                           type='directs')

# ============================================
# TABELA: PRODUCED_IN (Relação N:M)
# ============================================

@APP.route('/produced_in/')
def list_produced_in():
    """Lista todas as relações de produção (Tabela Produced_In)"""
    produced = db.execute('''
        SELECT pi.show_id, pi.country_id, c.title, co.name
        FROM Produced_In pi
        JOIN Content c ON pi.show_id = c.show_id
        JOIN Country co ON pi.country_id = co.country_id
        LIMIT 100
    ''').fetchall()
    return render_template('relationship-list.html', 
                           title="Tabela: Produced_In (Produzido Em)", 
                           items=produced, 
                           type='produced_in')

@APP.route('/produced_in/<show_id>/<int:country_id>/')
def get_produced_in(show_id, country_id):
    """Detalhe de uma linha específica da tabela Produced_In"""
    relation = db.execute('''
        SELECT c.title, co.name, c.show_id, co.country_id
        FROM Produced_In pi
        JOIN Content c ON pi.show_id = c.show_id
        JOIN Country co ON pi.country_id = co.country_id
        WHERE pi.show_id = ? AND pi.country_id = ?
    ''', [show_id, country_id]).fetchone()

    if relation is None:
        abort(404, 'Relação Produced_In não encontrada')

    return render_template('relationship-detail.html', 
                           title="Detalhe Produced_In", 
                           data=relation, 
                           type='produced_in')


# ============================================
# ADVANCED ANALYTICAL QUERIES (1-13)
# ============================================

@APP.route('/queries/<int:n>')
def query_handler(n):
    """
    Central handler for the 12 required analytical queries.
    Each query demonstrates different SQL techniques (Aggregation, JOINs, CTEs, Division).
    """
    
    # Query 1: Top 5 countries
    # Uses COUNT and JOIN to determine geographical volume
    if n == 1:
        sql = '''
            SELECT Country.name, COUNT(Produced_In.show_id) AS Total 
            FROM Country
            JOIN Produced_In ON Country.country_id = Produced_In.country_id 
            GROUP BY Country.name 
            ORDER BY Total DESC LIMIT 5
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html', 
                             query_number=1,
                             title="Distribuição Geográfica do Conteúdo",
                             subtitle="Quais são os 5 principais países com mais conteúdo disponível?",
                             results=results,
                             columns=["País", "Total de Conteúdos"],
                             sql_code=sql) 
    
    # Query 2: Most Versatile Actors
    # Uses COUNT(DISTINCT) on Genre IDs
    elif n == 2:
        sql = '''
            SELECT p.name, COUNT(DISTINCT bt.genre_id) as Unique_Genres
            FROM Participant p
            JOIN Acts_In ai ON p.participant_id = ai.participant_id
            JOIN Belongs_To bt ON ai.show_id = bt.show_id
            GROUP BY p.name
            ORDER BY Unique_Genres DESC LIMIT 5
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=2,
                             title="Versatilidade dos Atores",
                             subtitle="Qual o nome dos atores que participaram em mais géneros distintos?",
                             results=results,
                             columns=["Ator", "Géneros Únicos"],
                             sql_code=sql)
    
    # Query 3: Productive Directors
    # Uses HAVING clause to filter after grouping
    elif n == 3:
        sql = '''
            SELECT p.name, COUNT(d.show_id) as Obras
            FROM Participant p
            JOIN Directs d ON p.participant_id = d.participant_id
            GROUP BY p.name
            HAVING Obras > 5
            ORDER BY Obras DESC
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=3,
                             title="Produtividade dos Realizadores",
                             subtitle="Quais são os realizadores com mais de 5 TV shows ou filmes?",
                             results=results,
                             columns=["Diretor", "Número de Obras"],
                             sql_code=sql)
    
    # Query 4: Frequent Collaborations
    # Self-join on Participant via Acts_In and Directs
    elif n == 4:
        sql = '''
            SELECT dir.name as Diretor, act.name as Ator, COUNT(*) as Colaboracoes
            FROM Directs d
            JOIN Acts_In ai ON d.show_id = ai.show_id
            JOIN Participant dir ON d.participant_id = dir.participant_id
            JOIN Participant act ON ai.participant_id = act.participant_id
            WHERE dir.participant_id != act.participant_id
            GROUP BY dir.name, act.name
            ORDER BY Colaboracoes DESC LIMIT 5
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=4,
                             title="Colaborações Recorrentes",
                             subtitle="Quais são as duplas (Diretor-Ator) mais frequentes?",
                             results=results,
                             columns=["Diretor", "Ator", "Colaborações"],
                             sql_code=sql)
    
    # Query 5: Longest Movie per Genre
    # Filters only for 'Movie' type
    elif n == 5:
        sql = '''
            SELECT g.name as Genre, c.title, MAX(c.duration)
            FROM Genre g
            JOIN Belongs_To bt ON g.genre_id = bt.genre_id
            JOIN Content c ON bt.show_id = c.show_id
            WHERE c.type = 'Movie' AND c.duration IS NOT NULL
            GROUP BY g.name
            ORDER BY g.name
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=5,
                             title="Filme Mais Longo por Género",
                             subtitle="Qual é o filme mais longo de cada género?",
                             results=results,
                             columns=["Género", "Título", "Duração"],
                             sql_code=sql)
    
    # Query 6: Series by Year
    elif n == 6:
        sql = '''
            SELECT release_year, COUNT(*) as Total_Series
            FROM Content
            WHERE type = 'TV Show'
            GROUP BY release_year
            ORDER BY Total_Series DESC
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=6,
                             title="Ano com Mais Séries",
                             subtitle="Quantas séries foram lançadas em cada ano?",
                             results=results,
                             columns=["Ano", "Total de Séries"],
                             sql_code=sql)
    
    # Query 7: Actors avoiding Comedy
    # Uses NOT IN subquery to exclude anyone associated with 'Comedy'
    elif n == 7:
        sql = '''
            SELECT p.name, COUNT(ai.show_id) as Total_Obras
            FROM Participant p
            JOIN Acts_In ai ON p.participant_id = ai.participant_id
            GROUP BY p.name
            HAVING Total_Obras >= 5
            AND p.participant_id NOT IN (
                SELECT DISTINCT ai2.participant_id
                FROM Acts_In ai2
                JOIN Belongs_To bt ON ai2.show_id = bt.show_id
                JOIN Genre g ON bt.genre_id = g.genre_id
                WHERE g.name = 'Comedy'
            )
            ORDER BY Total_Obras DESC LIMIT 10
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=7,
                             title="Atores sem Comédia",
                             subtitle="Quais são os atores com +5 obras mas nenhuma comédia?",
                             results=results,
                             columns=["Ator", "Total de Obras"],
                             sql_code=sql)
    
    # Query 8: Average Cast Size
    # Uses nested query to count cast first, then averages per genre
    elif n == 8:
        sql = '''
            SELECT g.name, ROUND(AVG(Cast_Size), 0) as Media_Atores
            FROM Genre g
            JOIN Belongs_To bt ON g.genre_id = bt.genre_id
            JOIN (
                SELECT show_id, COUNT(participant_id) as Cast_Size
                FROM Acts_In GROUP BY show_id
            ) as Sizes ON bt.show_id = Sizes.show_id
            GROUP BY g.name 
            ORDER BY Media_Atores DESC
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=8,
                             title="Tamanho do Elenco",
                             subtitle="Qual a média do número de elementos no elenco de cada género?",
                             results=results,
                             columns=["Género", "Média de Atores"],
                             sql_code=sql)
    
    # Query 9: Dominant Genre per Top Country
    # Uses CTE (Common Table Expression) to rank countries and then find mode genre
    elif n == 9:
        sql = '''
            WITH CountryGenreCounts AS (
                SELECT co.name as Country, g.name as Genre, COUNT(*) as Cnt
                FROM Country co
                JOIN Produced_In ai ON co.country_id = ai.country_id
                JOIN Belongs_To bt ON ai.show_id = bt.show_id
                JOIN Genre g ON bt.genre_id = g.genre_id
                GROUP BY co.name, g.name
            ),
            TopCountries AS (
                SELECT co.name 
                FROM Country co
                JOIN Produced_In ai ON co.country_id = ai.country_id 
                GROUP BY co.name 
                ORDER BY COUNT(*) DESC 
                LIMIT 5
            )
            SELECT cgc.Country, cgc.Genre, cgc.Cnt as Total
            FROM CountryGenreCounts cgc
            JOIN TopCountries tc ON cgc.Country = tc.name
            WHERE cgc.Cnt = (
                SELECT MAX(cgc2.Cnt)
                FROM CountryGenreCounts cgc2
                WHERE cgc2.Country = cgc.Country
            )
            ORDER BY Total DESC
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=9,
                             title="Dominância de Género por País",
                             subtitle="Para cada um dos 5 países com mais lançamentos, qual é o género mais predominante?",
                             results=results,
                             columns=["País", "Género Dominante", "Contagem"],
                             sql_code=sql)
    
    # Query 10: Multifaceted Participants
    # Checks intersection of Actors and Directors using HAVING count > 0 for both
    elif n == 10:
        sql = '''
            SELECT p.name,
                   COUNT(DISTINCT ai.show_id) as Obras_Como_Ator,
                   COUNT(DISTINCT d.show_id) as Obras_Como_Diretor
            FROM Participant p
            LEFT JOIN Acts_In ai ON p.participant_id = ai.participant_id
            LEFT JOIN Directs d ON p.participant_id = d.participant_id
            GROUP BY p.name
            HAVING Obras_Como_Ator > 0 AND Obras_Como_Diretor > 0
            ORDER BY (Obras_Como_Ator + Obras_Como_Diretor) DESC
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=10,
                             title="Participantes Multifacetados",
                             subtitle="Quais são os participantes que são tanto atores como diretores?",
                             results=results,
                             columns=["Participante", "Obras como Ator", "Obras como Diretor"],
                             sql_code=sql)

    # Query 11: Duration Comparison (CTE)
    # Compares Genre average vs Global average using CTE
    elif n == 11:
        sql = '''
            WITH MediaGeral AS (
                SELECT AVG(duration) AS media_duracao_total
                FROM Content
                WHERE duration IS NOT NULL
                AND type = 'Movie'
            )
            SELECT G.name AS Genre,
                   ROUND(AVG(C.duration),1) AS Media_Duracao_Genero
            FROM Content C 
            JOIN Belongs_to BT ON C.Show_id = BT.Show_id 
            JOIN Genre G ON BT.Genre_id = G.Genre_id
            WHERE C.type = 'Movie' 
            GROUP BY G.name 
            HAVING AVG(C.duration) > (SELECT media_duracao_total FROM MediaGeral)
            ORDER BY Media_Duracao_Genero DESC;
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=11,
                             title="Duração por Género vs Geral",
                             subtitle="Quais são os géneros com duração média superior à média geral?",
                             results=results,
                             columns=["Género", "Média de Duração"],
                             sql_code=sql)

    # Query 12: Relational Division
    # Finds participants who directed ALL content they acted in.
    # Implements "Double NOT EXISTS" pattern.
    elif n == 12:
        sql = '''
            WITH Participacoes AS (
                SELECT DISTINCT participant_id, show_id
                FROM Acts_In
            )
            SELECT P.name AS Nome_Participante
            FROM Participant P
            WHERE EXISTS (
                SELECT 1 
                FROM Participacoes PA 
                WHERE PA.participant_id = P.participant_id
            )
            AND NOT EXISTS (
                SELECT 1
                FROM Participacoes PA
                WHERE PA.participant_id = P.participant_id
                AND NOT EXISTS (
                    SELECT 1
                    FROM Directs D
                    WHERE D.participant_id = P.participant_id
                    AND D.show_id = PA.show_id
                )
            )
        '''
        results = db.execute(sql).fetchall()
        return render_template('query-result.html',
                             query_number=12,
                             title="Participantes Autores Totais",
                             subtitle="Quais são os participantes que dirigiram TODOS os conteúdos nos quais atuaram?",
                             results=results,
                             columns=["Participante"],
                             sql_code=sql)
    else:
        abort(404, f'Query {n} not found.')


# ============================================
# SEARCH FUNCTIONALITY
# ============================================

@APP.route('/search/')
def search():
    """Simple Full-Text Search on Title and Description using LIKE"""
    query = request.args.get('q', '')
    
    if not query:
        return render_template('search.html', results=None, query='')
    
    search_pattern = f'%{query}%'
    results = db.execute('''
        SELECT show_id, title, type, release_year, description
        FROM Content
        WHERE title LIKE ? OR description LIKE ?
        ORDER BY title
        LIMIT 50
    ''', [search_pattern, search_pattern]).fetchall()
    
    return render_template('search.html', results=results, query=query)

# ============================================
# AUTHORS PAGE
# ============================================

@APP.route('/authors/')
def authors():
    """Static page displaying Group 51 information."""
    return render_template('authors.html')


# Run the app directly (Alternative to server.py)
if __name__ == '__main__':
    APP.run(debug=True)