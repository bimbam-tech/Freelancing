from PIL import Image, ImageDraw, ImageFont

def photo_editing_main_par(data: dict, username: str):
    print(10)
    calories = str(int(data['calories']))
    proteins = str(int(data['proteins']))
    fats = str(int(data['fats']))
    carbs = str(int(data['carbs']))
    print(11)
    img = Image.open('./telegram_bot/tmp/photo_response/main.jpg')
    print(12)
    font = ImageFont.truetype(font=None,size=30)
    idraw = ImageDraw.Draw(img)
    print(13)
    idraw.text((2, 64), calories, font=font, fill=(0, 0, 0))
    idraw.text((209, 64), proteins, font=font, fill=(0, 0, 0))
    idraw.text((414, 64), carbs, font=font, fill=(0, 0, 0))
    idraw.text((619, 64), fats, font=font, fill=(0, 0, 0))
    print(14)
    img.save(f'./telegram_bot/tmp/photo_response/{username}.jpg')
    print(15)
    photo_editing(data['ingredients'], username)
    print(16)
    img.close()
        
def extra_column(username: str, px: int):
    print(28)
    im1 = Image.open(f'./telegram_bot/tmp/photo_response/{username}.jpg')
    im2 = Image.open('./telegram_bot/tmp/photo_response/extra_column.jpg')
    print(29)
    im1.paste(im2, (136, px))
    im1.save(f'./telegram_bot/tmp/photo_response/{username}.jpg', quality=95)
    print(30)
    im1.close()
    im2.close()
    
def elongation_photo(username: str):
    print(31)
    img = Image.open(f"./telegram_bot/tmp/photo_response/{username}.jpg")
    print(32)
    width, height = img.size
    print(33)
    new_width = width
    new_height = height+49
    print(34)
    new_img = Image.new("RGB", (new_width, new_height), (255, 255, 255))
    print(35)
    new_img.paste(img, (0, 0))
    print(36)
    white_square_size = width
    white_square = Image.new("RGB", (white_square_size, white_square_size), (250, 255, 255))
    print(37)
    new_img.paste(white_square, (0, height))
    print(38)
    new_img.save(f"./telegram_bot/tmp/photo_response/{username}.jpg")
    print(39)
    img.close()

def prov_text(text: str):
    if len(text) > 15:
        return text[:15]+'...'
    return text

def photo_editing(data: list, username: str):
    print(17)
    px = 180
    px1 = 214
    print(18)
    for ingredient in data:
        print('цикл')
        img = Image.open(f'./telegram_bot/tmp/photo_response/{username}.jpg')
        print(19)
        font = ImageFont.truetype("arial.ttf", size=30)
        print(20)
        idraw = ImageDraw.Draw(img)
        print(21)
        idraw.text((140, px), prov_text(ingredient['name']), font=font, fill=(0, 0, 0))
        idraw.text((478, px), str(ingredient['weight']), font=font, fill=(0, 0, 0))
        print(22)
        px+=48
        print(23)
        img.save(f'./telegram_bot/tmp/photo_response/{username}.jpg')
        print(24)
        elongation_photo(username)
        print(25)
        extra_column(username, px1)
        print(26)
        px1+=49
        print(27)
        img.close()