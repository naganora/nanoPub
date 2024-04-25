
# 2024.01.24, kyung, upgrade handling image tag and check out unused img files
# 2022.07.04, kyung, add rebuild and $FolderFilter
# 2022.07.01, kyung, init

# $env:LC_ALL='C.UTF-8'
[System.Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# to install poshgit : https://www.lesstif.com/gitbook/posh-git-power-shell-prompt-git-89555709.html

# PUBLIC
$FolderFilterDefault = '0*'
$opt='--css=../css/markdown7.css'

# PROTECTED
function Show-Usage {
    $scriptName = $MyInvocation.MyCommand.Name
    Write-Host "Generate md -> markdown -> html"
    Write-Host "Usage: $scriptName <build|clean|rebuild> [FolderFilter]"
    Write-Host "   eg: $scriptName build"
    Write-Host "   eg: $scriptName build 05*"
    Exit 1
}

function Convert-Md2Markdown {
    # .md 파일에서 include 해서 .markdown으로 작성, 다중 사용은 불가 
    [CmdletBinding()]
    Param([string] $md, [string] $markdown)

    $imgs = @()

    # @import [[도움말_요약]](../04. user manual/도움말_요약.md) 
    # @link [[도움말_요약]](../04. user manual/도움말_요약.md) 
    # ![[Pasted image 20220705094505.png]]
    $import_regex = "^(#{1,4})\s(@import)\s*\[\[(.*)\]\]\s*\((.*)\)"
    $link_regex = "(.*)(@link)\s*\[\[(.*)\]\]\s*\((.*)\)"
    $obsidian_image_regex = "!\[\[(.*)\]\]"
    $markdown_image_regex = "!\[(.*)\]\((.*)\)"

    $file = Get-Content -Encoding utf8 $md | ForEach-Object {
        if($_ -match $import_regex){
            $level_bias = $Matches[1]
            $cmd = $Matches[2]
            $link = $Matches[4]
            Write-Host "  - ${cmd}: $link"
            if( Test-Path -Path $link -PathType Leaf) {
                $txt = Get-Content -Encoding utf8 $link
                $txt -replace '^#', $level_bias
            } else {
                Write-Error "Import not found: [$link]"
            }
        } 
        elseif ($_ -match $link_regex)
        {
            $prefix = $Matches[1]
            $cmd = $Matches[2]
            $name = $Matches[3]
            $link = $Matches[4]
            Write-Host "  - ${cmd}: $link"
            if( Test-Path -Path $link -PathType Leaf) {
                $txt = "${prefix}[$name]($link)"
                $txt
            } else {
                $txt = "${prefix}[$name]($link)"
                $txt
                Write-Warning "Link not found: [$link]"
            }
        }
        elseif ($_ -match $obsidian_image_regex)
        {
            $cmd = 'image'
            $img = $Matches[1]
            $img = $img.replace("#center", "")
            # Write-Host "  - ${cmd}: $img"
            if( Test-Path -Path "./imgs/$img" -PathType Leaf) {
                #New-Item -ItemType Directory -Force -Path .imgs | Out-Null
                #Copy-Item "../imgsrc/$img" ".imgs/$img"
                $imgs += $img
                $txt = "![](./imgs/$img)"
                $txt
            } else {
                $txt = "![](unknown $img)"
                $txt
                Write-Warning "Image file not found: [./imgs/$img]"
            }
        }
        elseif ($_ -match $obsidian_image_regex)
        {
            Write-Warning "  - check markdown image: $_"
        }
        else 
        {
            $_
        }
    }    
    $file | Out-File -Encoding utf8 -FilePath $markdown    

    return $imgs
}

function Make-Subfolder {
    [CmdletBinding()]
    Param([string] $Folder, [ValidateSet('build', 'clean', 'rebuild')][string] $Order)
    Set-Location -Path $Folder
    $img_files = @()
    Write-Host ""
    Write-Host "# ${Order}: ${pwd}"
    # Write-Host "`e[5;36m ${Order}: ${pwd} `e[0m"

    Get-ChildItem -Path . -Filter *.md | Foreach-Object {
        $html = $_.Basename + '.html'
        $md = $_.Basename + '.md'
        $markdown = $_.Basename + '.markdown'
        switch($Order)
        {
            'clean'
            {
                if( Test-Path -Path $markdown -PathType Leaf) {
                    Write-Host - rm $markdown
                    Remove-Item $markdown
                }
                if( Test-Path -Path $html -PathType Leaf) {
                    Write-Host - rm $html
                    Remove-Item $html
                }
            }
            'build'
            {
                if( Test-Path -Path $markdown -PathType Leaf) {
                    $LastWriteTimeMarkdown = [datetime](Get-ItemProperty -Path "$markdown" -Name LastWriteTime).lastwritetime
                }
                else {
                    $LastWriteTimeMarkdown = [datetime]0
                }
                $LastWriteTimeMd = [datetime](Get-ItemProperty -Path "$md" -Name LastWriteTime).lastwritetime   
                # Write-Host TTT MD: $LastWriteTimeMd MARKDOWN: $LastWriteTimeMarkdown
                if( $LastWriteTimeMd -gt $LastWriteTimeMarkdown ) {
                    Write-Host "- $html"
                    $imgs = Convert-Md2Markdown $md $markdown 
                    # Write-Host "+++ IMGS $imgs"
                    $img_files += $imgs

                    # well works: 
                    pandoc "$markdown" -o "$html" -f markdown $opt --standalone --metadata pagetitle="$html"
                    Remove-Item $markdown
                    #  --toc --toc-depth=5

                    # to docx: pandoc "$markdown" -o "$html" -f markdown -t docx --toc --toc-depth=5 $opt --standalone --metadata pagetitle="$html"
                    # pandoc .\user_manual.md -o user.html -F mermaid-filter
                    # or
                    #$md = ConvertFrom-Markdown -OutputType PDF -Path .\test.md 
                    #$md.html | Out-File -Encoding utf8 .\test.html
                    ### ConvertFrom-Markdown -OutputType PDF            
                }
            }
        }
    }
    $folder_files = @()
    if( Test-Path -Path ./imgs ) {
        $folder_files = Get-ChildItem -Path ./imgs -Name
    }
    $img_files_dup = $img_files
    $img_files = $img_files_dup | Sort-Object | Get-Unique
    # Write-Host "====2+++++:( ${img_files.Count} [$img_files]"
    # Write-Host "=====-----:( ${folder_files.Count} [$folder_files]"
    if($img_files.Count -gt 0) {
        $diff = Compare-Object -ReferenceObject $img_files -DifferenceObject $folder_files -PassThru
        if( $diff.Count -gt 0) {
            foreach($file in $diff) {
                Write-Warning "Unused file found: [./imgs/${file}]"
            }
        }
    }

    if($Order -eq 'clean') {
        Get-ChildItem -Path . -Exclude *.md,imgs | ForEach-Object {
            Write-Host - CHECK to remove: $_ 
        }
    }

    Set-Location -Path ..
}

# proc args
if( $args.Count -eq 0 )
{
    Show-Usage
}
$cmd = $args[0]
$FolderFilter = if($args[1]) { $args[1] } else {$FolderFilterDefault}

# proc main
# Set-PSDebug -Trace 1
Write-Host -- $pwd --
Make-Subfolder -Folder _import -Order $cmd
Get-ChildItem . -Directory -Filter $FolderFilter |
    Foreach-Object {
        Make-Subfolder -Folder $_.Name -Order $cmd
    }
Set-PSDebug -Off
