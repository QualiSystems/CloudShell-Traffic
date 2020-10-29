
def create_html(json_list_object):

    html_template = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <meta http-equiv="X-UA-Compatible" content="ie=edge" />
      <title>CloudShell Reservation Info</title>
      <style>
        body {{ font-family: sans-serif; }}
        tbody tr {{ background-color: #bdd6ee; }}
        tbody tr.alt {{ background-color: #deeaf6; }}
        tbody td {{ padding: 10px; }}
        .error {{ background-color: #ED4337; font-weight: bold; }}
        .small-error-text {{ font-size: 80%; color: #ED4337; }}
        .small {{ font-size: 80% }}
      </style>
    </head>
    <body>
      <br />
      <p class="small">
      </p>
        {all_tables}
    </body>
    </html>
    '''

    one_table_result = '''
    <table>
        <colgroup><col /><col /></colgroup>
        <tbody>
          <tr class="alt"><td>Component Name:</td><td>{item_name}</td></tr>
          <tr><td>result:</td><td> <img alt="sign" src={image_src} /> </td></tr>
          <tr class="alt"><td>Status:</td><td>{status}</td></tr>
          <tr><td>Summary:</td><td>{summary_data}</td></tr>
          <tr class="alt"><td>log:</td><td>{log_data}</td></tr>
        </tbody>
      </table>
      <br><br><br>
    '''

    html_tables = ''
    for resource_name, command_out in json_list_object.items():
        json_object = command_out['report']
        summary_result = ''
        if json_object['result']:
            result_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAA4AAAAOCAYAAAAfSC3RAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAZdEVYdFNvZnR3YXJlAEFkb2JlIEltYWdlUmVhZHlxyWU8AAABR0lEQVQ4T42SzyuDcRyAl9NOyonsP5AiUrwvSn6UxoGbmq30OshFidNGKWflD6CkpSxJHBwcduHdQRoH28qvw8JpB9nC1tfneXvfbYdvcnjq0+fzPG/fw+tTSlU5yu43zpwMx4KH3emRg/YiMLPjVu96Q8Pm5UrbZKInN3XepUJ2n5q7GXBgZscNB7caXr9dNU8f9z6EU4ay0oNauInzaOeTLV7oX7qY3for8sDBpSFstZLjzzpRi7jSBAg7Iqn+ilbSIG6ZhtCcTw/9O1y4HSU0nTCWiRR0ko7ofbggjeE8Nf6ybeskHbg0hIHPn4/VaCZU0on14ODSEPoFM198iq9nI9+6ANbkhoNLQwhNQvCrUto5fd973chZ5cW7MQXM7LiJM+G6tV/OXfC1ZWFXOHNhZscNp/bL1cGzA0KnYLgws+Pmesr3C3ALDRUfKEH6AAAAAElFTkSuQmCC'
        else:
            result_image = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABEAAAAQCAYAAADwMZRfAAAAAXNSR0IArs4c6QAAAARnQU1BAACxjwv8YQUAAAAZdEVYdFNvZnR3YXJlAEFkb2JlIEltYWdlUmVhZHlxyWU8AAABYUlEQVQ4T5WSO0vDYBiFrVKjtIooiLeKqFAHLYIFLwhKcXMTncTV1aU4+g+c6uZikeIgtIEi1YqIg4JWCoIXdHSzQ11E0CW+T2li/JJS+8HDl/e85xwCSZ1hGJXwHoam1ne1jg9uZmVv4SoKntfM6VCqrb+Y03oMud+Z0RVfCYdQplmfWdi71rqNvJRwyxxHV3wlHIJQf7cdmz7y9X5RYCLzNzp7xe9a0pIcnTy7tRUAMzp7xe8oabjc2FzJal1WmGM+o7PHJ1g5ewG0JwfGnsyQWgLs8QlWzl7gzS6vRS8af98COPaZ/cnSahS/8LekeP8Y0DuHC/ZAJfAVcvmAWtKUjizGrsqftBr4xL9DzizxvOwfhNKtfZ9uAY6bjv85nhgnT4kvFZ7Tb/75Fib4yZGnZPBYfiQ3YzXIkack/DAReXMzVYMceUqCwpaQEc5rAD+5ICV+YUSYFeZrAL/kDP8PZcWvF8hpo+0AAAAASUVORK5CYII='

        summary_info = json_object['summary']
        for k,v in summary_info.items():
            summary_result += '{0} - {1} <br>'.format(k, v)

        one_table_processed = one_table_result.format(
            status=json_object['status'],
            image_src=result_image,
            log_data=json_object['log'],
            summary_data=summary_result,
            item_name=json_object['name']
        )
        html_tables += one_table_processed

    html_message = html_template.format(
        all_tables=html_tables
    )

    return html_message
