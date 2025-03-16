-----------------------------------------------------------------
-- tikz_img.lua
--
-- Gabriel Braun, 2023
-----------------------------------------------------------------

local src_path
local tmp_path

local function getMetadata(meta)
    --
    -- Extrai metadados.
    --
    tmp_path = meta.tmp_path
    src_path = meta.src_path
    return meta
end

local function Image(elem)
    --
    -- Substituir um .pdf referente a um .svg.
    --
    local img_name, img_ext = pandoc.path.split_extension(elem.src)

    if img_ext == ".svg" then
        local svg_path = pandoc.path.join { src_path, img_name .. ".svg" }
        local pdf_path = pandoc.path.join { tmp_path, img_name .. ".pdf" }

        os.execute("cairosvg -s 1.33 " .. svg_path .. " -o " .. pdf_path)

        elem.src = pdf_path
    else
        elem.src = pandoc.path.filename(elem.src)
    end

    return elem
end

-----------------------------------------------------------------
-- Filtro
-----------------------------------------------------------------

return {
    {
        Meta = getMetadata
    },
    {
        Image = Image
    }
}
